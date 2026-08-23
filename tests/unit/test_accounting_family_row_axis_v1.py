from __future__ import annotations

import copy
import hashlib
import io

import pytest
from PIL import Image, ImageDraw

from bctc_ai.evaluation import accounting_family_row_axis_v1 as row_axis_v1
from bctc_ai.evaluation import family_first_authenticated_page_region_v1 as region_v1
from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    AccountingFamilyRowAxisV1Error,
    build_accounting_family_row_axis_for_topology_region_v1,
    build_accounting_family_row_axis_v1,
    validate_accounting_family_row_axis_replay_v1,
)
from bctc_ai.evaluation.adaptive_accounting_table_geometry_v1 import (
    propose_missing_value_lane_regions_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _spec(*, continuation_pages: int = 1) -> dict[str, object]:
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
            "max_continuation_pages": continuation_pages,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Phân tích dư nợ theo thời gian"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "LOAN_MATURITY",
        },
        "structural_reset_aliases": ["Phân tích cho vay theo ngành"],
    }


def _contextual_summary_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "matchers": [{"aliases": ["Tiền gửi tại TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [{"aliases": ["Bằng VND"], "within_role": "DEPOSIT_GROUP"}],
                "presence": "OPTIONAL",
                "role": "DEPOSIT_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "matchers": [{"aliases": ["Cho vay TCTD khác"], "within_role": None}],
                "presence": "OPTIONAL",
                "role": "LOAN_GROUP",
                "role_kind": "STRUCTURAL_GROUP",
            },
            {
                "matchers": [{"aliases": ["Bằng VND"], "within_role": "LOAN_GROUP"}],
                "presence": "OPTIONAL",
                "role": "LOAN_VND",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "INTERBANK",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay các TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEPOSIT_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": [],
    }


def _line(
    ordinal: int,
    semantic: str,
    numeric: str,
    bbox: list[int],
    *,
    page: int = 1,
) -> dict[str, object]:
    sample = (page - 1) * 100 + ordinal + 1
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
        "vietocr_text": semantic,
    }


def _page(lines: list[dict[str, object]], page_sequence: int = 1) -> dict[str, object]:
    return {"lines": lines, "page_sequence": page_sequence, "page_width": 1000}


def _ordinary_pages() -> list[dict[str, object]]:
    return [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Nợ ngắn hạn", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Nợ trung hạn", "", [50, 150, 300, 172]),
                _line(7, "200", "200", [600, 150, 700, 172]),
                _line(8, "180", "180", [800, 150, 900, 172]),
                _line(9, "300", "300", [600, 200, 700, 222]),
                _line(10, "270", "270", [800, 200, 900, 222]),
            ]
        )
    ]


def _dash_region(
    raw_pixel_bbox: list[int], *, blank: bool = False, degraded_short_mark: bool = False
) -> dict[str, object]:
    image = Image.new("RGB", (42, 27), "white")
    if not blank:
        ImageDraw.Draw(image).rectangle(
            (16, 11, 17, 13) if degraded_short_mark else (16, 11, 25, 15),
            fill="black",
        )
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=False, compress_level=9)
    payload = stream.getvalue()
    material = {
        "authority": dict(region_v1._REGION_AUTHORITY),
        "document_ordinal": 1,
        "format_version": region_v1.FORMAT_VERSION,
        "index_id": "index",
        "ink_localization_status": "GLYPH_COMPONENT_TIGHTENED_WITHIN_PROPOSED_CELL",
        "physical_page": 1,
        "proposed_raw_pixel_bbox": list(raw_pixel_bbox),
        "recognition_raw_pixel_bbox": list(raw_pixel_bbox),
        "region_png_ref": {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
        "render_id": "render",
        "render_ref": {
            "pixel_height": 1200,
            "pixel_width": 1000,
            "sha256": "1" * 64,
            "size_bytes": 100,
        },
        "state": "AUTHENTICATED_RENDER_CALLER_PROPOSED_REGION_CROP",
        "white_border": [12, 8, 12, 8],
    }
    return {
        **material,
        "region_id": "ffaprv1:region:" + canonical_json_sha256_v1(material),
        "region_png_bytes": payload,
    }


def test_visible_rows_bind_to_body_derived_lane_ordinals() -> None:
    result = build_accounting_family_row_axis_v1(_ordinary_pages(), _spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["metrics"] == {
        "bound_value_count": 4,
        "complete_trailing_value_row_count": 1,
        "missing_lane_count": 0,
        "optional_label_only_blank_lane_count": 0,
        "optional_label_only_row_count": 0,
        "optional_partial_blank_lane_count": 0,
        "optional_partial_row_count": 0,
        "partial_trailing_value_row_count": 0,
        "partial_row_count": 0,
        "role_row_count": 2,
        "trailing_value_row_count": 1,
        "unresolved_empty_row_count": 0,
        "visible_dash_rescue_attempt_count": 0,
        "visible_dash_zero_count": 0,
    }
    assert [row["role"] for row in result["rows"]] == ["SHORT_TERM", "MEDIUM_TERM"]
    assert [value["column_ordinal"] for value in result["rows"][0]["values"]] == [0, 1]
    assert [value["parsed_token"]["coefficient"] for value in result["rows"][1]["values"]] == [
        200,
        180,
    ]
    assert [
        value["parsed_token"]["coefficient"] for value in result["trailing_value_rows"][0]["values"]
    ] == [300, 270]
    assert result["safety"]["detector_geometry_treated_as_numeric_recognition"] is False


def test_wrapped_label_does_not_consume_interleaved_numeric_value_cells() -> None:
    pages = [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Nợ", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "ngắn hạn", "", [50, 126, 300, 148]),
                _line(7, "Nợ trung hạn", "", [50, 180, 300, 202]),
                _line(8, "200", "200", [600, 180, 700, 202]),
                _line(9, "180", "180", [800, 180, 900, 202]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    short = next(row for row in result["rows"] if row["role"] == "SHORT_TERM")
    assert short["label_match"]["source_line_indices"] == [3, 6]
    assert [value["raw_prediction"] for value in short["values"]] == ["100", "90"]


def test_complete_period_unit_header_recovers_all_dash_body_column_geometry() -> None:
    pages = [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Triệu đồng", "", [600, 75, 700, 95]),
                _line(4, "Triệu đồng", "", [800, 75, 900, 95]),
                _line(5, "Nợ ngắn hạn", "", [50, 120, 300, 142]),
                _line(6, "Nợ trung hạn", "", [50, 180, 300, 202]),
            ]
        )
    ]
    base = build_accounting_family_row_axis_v1(pages, _spec())

    assert base["column_grids"][0]["geometry_status"] == (
        "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID"
    )
    assert base["column_grids"][0]["column_centers"] == [650.0, 850.0]
    rescues = []
    for row in base["rows"]:
        centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(
            base["rows"], row, base["column_grids"]
        )
        proposals = propose_missing_value_lane_regions_v1(
            row_axis_v1._region_lines(pages, base["topology_region"])[1],
            label_boxes=[
                line["bbox"]
                for line in pages[0]["lines"]
                if line["line_ordinal"] == row["label_match"]["source_line_index"]
            ],
            is_numeric=row_axis_v1._is_numeric,
            page_width=1000,
            page_height=1200,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible_cells,
        )
        rescues.extend(
            {
                "column_ordinal": proposal["column_ordinal"],
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"]),
                "role": row["role"],
            }
            for proposal in proposals
        )

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=tuple(rescues),
    )

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["metrics"]["visible_dash_zero_count"] == 4
    assert all(
        [value["parsed_token"]["coefficient"] for value in row["values"]] == [0, 0]
        for row in result["rows"]
    )


def test_structural_groups_emit_only_complete_noncoextensive_inline_values() -> None:
    summary = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Cho vay TCTD khác", "", [50, 150, 300, 172]),
                _line(7, "20", "20", [600, 150, 700, 172]),
                _line(8, "10", "10", [800, 150, 900, 172]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(summary, _contextual_summary_spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [row["role"] for row in result["rows"]] == ["DEPOSIT_GROUP", "LOAN_GROUP"]
    assert all(row["role_kind"] == "STRUCTURAL_GROUP" for row in result["rows"])
    assert [value["raw_prediction"] for value in result["rows"][0]["values"]] == [
        "100",
        "90",
    ]


def test_label_only_structural_groups_do_not_borrow_child_values() -> None:
    detail = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 90, 300, 112]),
                _line(4, "Bằng VND", "", [80, 130, 300, 152]),
                _line(5, "100", "100", [600, 130, 700, 152]),
                _line(6, "90", "90", [800, 130, 900, 152]),
                _line(7, "Cho vay TCTD khác", "", [50, 190, 300, 212]),
                _line(8, "Bằng VND", "", [80, 230, 300, 252]),
                _line(9, "20", "20", [600, 230, 700, 252]),
                _line(10, "10", "10", [800, 230, 900, 252]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(detail, _contextual_summary_spec())

    assert [row["role"] for row in result["rows"]] == ["DEPOSIT_VND", "LOAN_VND"]
    used = [value["sample_id"] for row in result["rows"] for value in row["values"]]
    assert len(used) == len(set(used))


def test_complete_child_row_axis_overrides_staggered_structural_group_affinity() -> None:
    detail = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 90, 300, 124]),
                _line(4, "Bằng VND", "", [80, 120, 300, 154]),
                # Detector boxes for one visual row are staggered enough that
                # one lane independently prefers the structural parent.
                _line(5, "100", "100", [600, 105, 700, 139]),
                _line(6, "90", "90", [800, 95, 900, 135]),
                _line(7, "Cho vay TCTD khác", "", [50, 190, 300, 224]),
                _line(8, "Bằng VND", "", [80, 220, 300, 254]),
                _line(9, "20", "20", [600, 205, 700, 239]),
                _line(10, "10", "10", [800, 195, 900, 235]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(detail, _contextual_summary_spec())

    assert [row["role"] for row in result["rows"]] == ["DEPOSIT_VND", "LOAN_VND"]
    assert [[value["raw_prediction"] for value in row["values"]] for row in result["rows"]] == [
        ["100", "90"],
        ["20", "10"],
    ]
    assert result["safety"]["staggered_lane_bboxes_bound_by_complete_parent_child_row_axis"]


def test_cluster_reassignment_updates_both_source_and_target_missing_lane_axes() -> None:
    def value(sample: str, lane: int, left: int) -> dict[str, object]:
        return {
            "bbox": [left, 105, left + 80, 139],
            "column_center": float(left + 40),
            "column_ordinal": lane,
            "crop_ref": {"path": sample, "sha256": "a" * 64, "size_bytes": 1},
            "line_ordinal": lane,
            "page_sequence": 1,
            "parsed_token": {
                "classification": "SIGNED_NUMBER",
                "coefficient": lane + 1,
                "negative_parentheses": False,
                "normalized_token": str(lane + 1),
                "percentage_mark_present": False,
                "scale": 0,
                "separator_interpretation": "NONE",
                "sign": 1,
            },
            "raw_prediction": str(lane + 1),
            "reader_score": 1.0,
            "row_affinity": 1.0,
            "sample_id": sample,
        }

    rows = [
        {
            "_label_vertical_center": 107.0,
            "_lane_count": 2,
            "label_match": {"matched_within_role": None, "page_sequence": 1},
            "missing_column_ordinals": [],
            "role": "GROUP",
            "role_kind": "STRUCTURAL_GROUP",
            "status": "VISIBLE_VALUE_LANES_BOUND",
            "values": [value("sample-1", 0, 600), value("sample-2", 1, 800)],
        },
        {
            "_label_vertical_center": 137.0,
            "_lane_count": 2,
            "label_match": {"matched_within_role": "GROUP", "page_sequence": 1},
            "missing_column_ordinals": [0, 1],
            "role": "CHILD",
            "role_kind": "ADDITIVE_CHILD",
            "status": "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL",
            "values": [],
        },
    ]

    rebound = row_axis_v1._enforce_exclusive_source_cells(rows)

    by_role = {row["role"]: row for row in rebound}
    assert by_role["GROUP"]["values"] == []
    assert by_role["GROUP"]["missing_column_ordinals"] == [0, 1]
    assert [item["sample_id"] for item in by_role["CHILD"]["values"]] == [
        "sample-1",
        "sample-2",
    ]
    assert by_role["CHILD"]["missing_column_ordinals"] == []


def test_valued_parent_cluster_is_not_reassigned_to_distant_child() -> None:
    detail = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Bằng VND", "", [80, 230, 300, 252]),
                _line(7, "80", "80", [600, 230, 700, 252]),
                _line(8, "70", "70", [800, 230, 900, 252]),
                _line(9, "Cho vay TCTD khác", "", [50, 300, 300, 322]),
                _line(10, "20", "20", [600, 300, 700, 322]),
                _line(11, "10", "10", [800, 300, 900, 322]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(detail, _contextual_summary_spec())

    by_role = {row["role"]: row for row in result["rows"]}
    assert [value["raw_prediction"] for value in by_role["DEPOSIT_GROUP"]["values"]] == [
        "100",
        "90",
    ]
    assert [value["raw_prediction"] for value in by_role["DEPOSIT_VND"]["values"]] == [
        "80",
        "70",
    ]


def test_optional_blank_child_under_valued_structural_parent_is_label_only() -> None:
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Bằng VND", "", [80, 150, 300, 172]),
                _line(7, "Cho vay TCTD khác", "", [50, 220, 300, 242]),
                _line(8, "20", "20", [600, 220, 700, 242]),
                _line(9, "10", "10", [800, 220, 900, 242]),
            ]
        )
    ]
    base = build_accounting_family_row_axis_v1(pages, _contextual_summary_spec())
    child = next(row for row in base["rows"] if row["role"] == "DEPOSIT_VND")
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], child)
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][child["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    rescues = tuple(
        {
            "column_ordinal": proposal["column_ordinal"],
            "page_sequence": 1,
            "region": _dash_region(proposal["raw_pixel_bbox"], blank=True),
            "role": "DEPOSIT_VND",
        }
        for proposal in proposals
    )

    result = build_accounting_family_row_axis_v1(
        pages,
        _contextual_summary_spec(),
        visible_dash_rescues=rescues,
    )

    child = next(row for row in result["rows"] if row["role"] == "DEPOSIT_VND")
    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert child["status"] == "VISIBLE_OPTIONAL_LABEL_ONLY_NO_VALUE_CELLS"
    assert child["values"] == []
    assert child["missing_column_ordinals"] == [0, 1]
    assert result["metrics"]["optional_label_only_row_count"] == 1
    assert result["metrics"]["optional_label_only_blank_lane_count"] == 2
    assert result["metrics"]["missing_lane_count"] == 0


def test_optional_partial_child_with_blank_missing_lane_does_not_block_complete_parent() -> None:
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Bằng VND", "", [80, 150, 300, 172]),
                _line(7, "70", "70", [800, 150, 900, 172]),
                _line(8, "Cho vay TCTD khác", "", [50, 220, 300, 242]),
                _line(9, "20", "20", [600, 220, 700, 242]),
                _line(10, "10", "10", [800, 220, 900, 242]),
            ]
        )
    ]
    base = build_accounting_family_row_axis_v1(pages, _contextual_summary_spec())
    child = next(row for row in base["rows"] if row["role"] == "DEPOSIT_VND")
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(
        base["rows"], child, base["column_grids"]
    )
    proposal = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][child["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )[0]

    result = build_accounting_family_row_axis_v1(
        pages,
        _contextual_summary_spec(),
        visible_dash_rescues=(
            {
                "column_ordinal": proposal["column_ordinal"],
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"], blank=True),
                "role": "DEPOSIT_VND",
            },
        ),
    )

    child = next(row for row in result["rows"] if row["role"] == "DEPOSIT_VND")
    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert child["status"] == "VISIBLE_OPTIONAL_PARTIAL_VALUE_ROW_WITH_BLANK_LANES"
    assert [value["raw_prediction"] for value in child["values"]] == ["70"]
    assert child["missing_column_ordinals"] == [0]
    assert result["metrics"]["optional_partial_row_count"] == 1
    assert result["metrics"]["optional_partial_blank_lane_count"] == 1
    assert result["metrics"]["missing_lane_count"] == 0


def test_later_child_with_explicit_other_parent_does_not_hide_structural_row() -> None:
    rows = [
        {
            "label_match": {"matched_within_role": None},
            "role": "VISIBLE_PARENT",
            "role_kind": "STRUCTURAL_GROUP",
            "status": "VISIBLE_VALUE_LANES_BOUND",
        },
        {
            "label_match": {"matched_within_role": None},
            "role": "PARENT_REQUIRING_PIXEL_RESCUE",
            "role_kind": "STRUCTURAL_GROUP",
            "status": "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL",
        },
        {
            "label_match": {"matched_within_role": "VISIBLE_PARENT"},
            "role": "LATER_ALTERNATE_VIEW_CHILD",
            "role_kind": "ADDITIVE_CHILD",
            "status": "VISIBLE_VALUE_LANES_BOUND",
        },
    ]

    assert row_axis_v1._structural_roles_with_complete_children(rows) == {"VISIBLE_PARENT"}


def test_pixel_rescued_children_prevent_header_rules_from_becoming_parent_values() -> None:
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "Bằng VND", "", [80, 150, 300, 172]),
                _line(5, "Cho vay TCTD khác", "", [50, 220, 300, 242]),
                _line(6, "20", "20", [600, 220, 700, 242]),
                _line(7, "10", "10", [800, 220, 900, 242]),
            ]
        )
    ]
    base = build_accounting_family_row_axis_v1(pages, _contextual_summary_spec())
    rescues = []
    for row in base["rows"]:
        if row["role"] not in {"DEPOSIT_GROUP", "DEPOSIT_VND"}:
            continue
        centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], row)
        proposals = propose_missing_value_lane_regions_v1(
            [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
            label_boxes=[pages[0]["lines"][row["label_match"]["source_line_index"]]["bbox"]],
            is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
            page_width=1000,
            page_height=1200,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible_cells,
        )
        rescues.extend(
            {
                "column_ordinal": proposal["column_ordinal"],
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"]),
                "role": row["role"],
            }
            for proposal in proposals
        )

    result = build_accounting_family_row_axis_v1(
        pages,
        _contextual_summary_spec(),
        visible_dash_rescues=tuple(rescues),
    )

    by_role = {row["role"]: row for row in result["rows"]}
    assert "DEPOSIT_GROUP" not in by_role
    assert [
        value["parsed_token"]["classification"] for value in by_role["DEPOSIT_VND"]["values"]
    ] == [
        "DASH_ZERO",
        "DASH_ZERO",
    ]


def test_optional_blank_structural_group_remains_topology_only() -> None:
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "Cho vay TCTD khác", "", [50, 220, 300, 242]),
                _line(5, "20", "20", [600, 220, 700, 242]),
                _line(6, "10", "10", [800, 220, 900, 242]),
            ]
        )
    ]
    base = build_accounting_family_row_axis_v1(pages, _contextual_summary_spec())
    parent = next(row for row in base["rows"] if row["role"] == "DEPOSIT_GROUP")
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], parent)
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][parent["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )

    result = build_accounting_family_row_axis_v1(
        pages,
        _contextual_summary_spec(),
        visible_dash_rescues=tuple(
            {
                "column_ordinal": proposal["column_ordinal"],
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"], blank=True),
                "role": "DEPOSIT_GROUP",
            }
            for proposal in proposals
        ),
    )

    assert [row["role"] for row in result["rows"]] == ["LOAN_GROUP"]
    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"


def test_missing_recognized_cell_keeps_actual_comparative_lane_and_requires_rescue() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][7]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }

    result = build_accounting_family_row_axis_v1(pages, _spec())

    medium = result["rows"][1]
    assert result["status"] == "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
    assert medium["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    assert medium["missing_column_ordinals"] == [0]
    assert medium["values"][0]["column_ordinal"] == 1
    assert medium["values"][0]["raw_prediction"] == "180"


def _all_comparison_dash_pages() -> list[dict[str, object]]:
    return [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "30.06.2025", "30.06.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Triệu đồng", "Triệu đồng", [600, 75, 700, 97]),
                _line(4, "Triệu đồng", "Triệu đồng", [800, 75, 900, 97]),
                _line(5, "Nợ ngắn hạn", "", [50, 120, 300, 142]),
                _line(6, "100", "100", [600, 120, 700, 142]),
                _line(7, "Nợ trung hạn", "", [50, 170, 300, 192]),
                _line(8, "200", "200", [600, 170, 700, 192]),
            ]
        )
    ]


def test_period_and_unit_headers_recover_detector_missing_comparison_column_geometry() -> None:
    result = build_accounting_family_row_axis_v1(_all_comparison_dash_pages(), _spec())

    assert result["status"] == "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[1], [1]]
    assert [row["values"][0]["column_ordinal"] for row in result["rows"]] == [0, 0]
    assert [row["values"][0]["column_center"] for row in result["rows"]] == [650.0, 650.0]
    assert result["column_grids"] == [
        {
            "column_centers": [650.0, 850.0],
            "geometry_status": "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID",
            "header_evidence_source_line_indices": [1, 2, 3, 4],
            "page_sequence": 1,
        }
    ]


def test_visual_header_recovers_grid_when_provider_orders_header_after_first_body_row() -> None:
    pages = [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "Nợ ngắn hạn", "", [50, 120, 300, 142]),
                _line(2, "100", "100", [600, 120, 700, 142]),
                _line(3, "30.06.2025", "30.06.2025", [600, 50, 700, 72]),
                _line(4, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(5, "Triệu đồng", "", [600, 75, 700, 97]),
                _line(6, "Triệu đồng", "", [800, 75, 900, 97]),
                _line(7, "Nợ trung hạn", "", [50, 170, 300, 192]),
                _line(8, "200", "200", [600, 170, 700, 192]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["column_grids"] == [
        {
            "column_centers": [650.0, 850.0],
            "geometry_status": "LOCAL_PERIOD_AND_UNIT_HEADER_SUPPORTED_COLUMN_GRID",
            "header_evidence_source_line_indices": [3, 4, 5, 6],
            "page_sequence": 1,
        }
    ]
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[1], [1]]


def test_header_column_completion_requires_a_coextensive_unit_axis() -> None:
    pages = _all_comparison_dash_pages()
    pages[0]["lines"][4]["vietocr_text"] = ""
    pages[0]["lines"][4]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[], []]
    assert {value["column_ordinal"] for row in result["rows"] for value in row["values"]} == {0}


def test_header_column_completion_rejects_period_unit_geometry_disagreement() -> None:
    pages = _all_comparison_dash_pages()
    pages[0]["lines"][4]["bbox"] = [430, 75, 530, 97]

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[], []]


def test_body_grid_can_remain_empty_when_no_numeric_cell_is_recognized() -> None:
    pages = _ordinary_pages()
    for line in pages[0]["lines"]:
        line["numeric_recognition"] = {"raw_prediction": "", "reader_score": 0.2}

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["status"] == "ROW_AXIS_PROPOSAL_WITH_UNRESOLVED_CELLS"
    assert result["column_grids"] == [
        {
            "column_centers": [],
            "geometry_status": "BODY_DERIVED_NUMERIC_COLUMN_GRID",
            "header_evidence_source_line_indices": [],
            "page_sequence": 1,
        }
    ]
    assert [row["status"] for row in result["rows"]] == [
        "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL",
        "UNRESOLVED_NO_VISIBLE_RECOGNIZED_VALUE_CELL",
    ]


def test_header_supported_grid_can_crop_and_replay_the_visible_dash_cells() -> None:
    pages = _all_comparison_dash_pages()
    base = build_accounting_family_row_axis_v1(pages, _spec())
    rescues = []
    for row in base["rows"]:
        centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(
            base["rows"], row, base["column_grids"]
        )
        label = row["label_match"]
        proposals = propose_missing_value_lane_regions_v1(
            [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
            label_boxes=[pages[0]["lines"][label["source_line_index"]]["bbox"]],
            is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
            page_width=1000,
            page_height=1200,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible_cells,
        )
        proposal = next(item for item in proposals if item["column_ordinal"] == 1)
        rescues.append(
            {
                "column_ordinal": 1,
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"]),
                "role": row["role"],
            }
        )

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=tuple(rescues),
    )

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[], []]
    assert [[value["raw_prediction"] for value in row["values"]] for row in result["rows"]] == [
        ["100", "-"],
        ["200", "-"],
    ]
    assert result["metrics"]["visible_dash_zero_count"] == 2


def test_pixel_replayed_dash_completes_only_the_body_grid_missing_lane() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][7]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    base = build_accounting_family_row_axis_v1(pages, _spec())
    medium = base["rows"][1]
    label = medium["label_match"]
    region_lines = [
        {**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]
    ]
    proposals = propose_missing_value_lane_regions_v1(
        region_lines,
        label_boxes=[pages[0]["lines"][label["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        retain_singleton_columns=False,
    )
    proposal = next(item for item in proposals if item["column_ordinal"] == 0)
    rescue = {
        "column_ordinal": 0,
        "page_sequence": 1,
        "region": _dash_region(proposal["raw_pixel_bbox"]),
        "role": "MEDIUM_TERM",
    }

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=(rescue,),
    )

    medium = result["rows"][1]
    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert medium["missing_column_ordinals"] == []
    assert [value["column_ordinal"] for value in medium["values"]] == [0, 1]
    assert medium["values"][0]["parsed_token"]["classification"] == "DASH_ZERO"
    assert medium["values"][0]["parsed_token"]["coefficient"] == 0
    assert result["metrics"]["visible_dash_rescue_attempt_count"] == 1
    assert result["metrics"]["visible_dash_zero_count"] == 1
    assert result["visible_dash_rescues"][0]["classification"] == ("VISIBLE_HORIZONTAL_DASH_GLYPH")


def test_geometry_binds_value_even_when_provider_reading_order_precedes_label() -> None:
    pages = _ordinary_pages()
    lines = pages[0]["lines"]
    lines[3], lines[4] = lines[4], lines[3]
    for ordinal, line in enumerate(lines):
        line["line_ordinal"] = ordinal

    result = build_accounting_family_row_axis_v1(pages, _spec())

    short = result["rows"][0]
    assert short["status"] == "VISIBLE_VALUE_LANES_BOUND"
    assert [value["raw_prediction"] for value in short["values"]] == ["100", "90"]


def test_standalone_footnote_extends_only_the_preceding_label_geometry() -> None:
    spec = _spec()
    spec["parent"]["aliases"] = ["Tiền gửi và cho vay các TCTD khác"]
    spec["children"][0]["aliases"] = ["Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành"]
    spec["children"][1]["aliases"] = ["Cho vay TCTD khác"]
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(
                    3,
                    "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
                    "",
                    [50, 100, 520, 122],
                ),
                _line(4, "(ii)", "", [50, 122, 90, 144]),
                _line(5, "100", "100", [600, 122, 700, 144]),
                _line(6, "90", "90", [800, 122, 900, 144]),
                _line(7, "Cho vay TCTD khác", "", [50, 175, 300, 197]),
                _line(8, "20", "20", [600, 175, 700, 197]),
                _line(9, "10", "10", [800, 175, 900, 197]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(pages, spec)

    row = next(item for item in result["rows"] if item["role"] == "SHORT_TERM")
    assert [value["raw_prediction"] for value in row["values"]] == ["100", "90"]
    assert row["label_match"]["end_source_line_index"] == 3


def test_numeric_reader_can_rescue_geometry_of_misread_standalone_footnote() -> None:
    spec = _spec()
    spec["parent"]["aliases"] = ["Tiền gửi và cho vay các TCTD khác"]
    spec["children"][0]["aliases"] = ["Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành"]
    spec["children"][1]["aliases"] = ["Cho vay TCTD khác"]
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(
                    3,
                    "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
                    "",
                    [50, 100, 520, 122],
                ),
                _line(4, "0", "(i)", [50, 122, 90, 144]),
                _line(5, "100", "100", [600, 122, 700, 144]),
                _line(6, "90", "90", [800, 122, 900, 144]),
                _line(7, "Cho vay TCTD khác", "", [50, 175, 300, 197]),
                _line(8, "20", "20", [600, 175, 700, 197]),
                _line(9, "10", "10", [800, 175, 900, 197]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(pages, spec)

    row = next(item for item in result["rows"] if item["role"] == "SHORT_TERM")
    assert [value["raw_prediction"] for value in row["values"]] == ["100", "90"]
    assert row["label_match"]["end_source_line_index"] == 3


def test_year_like_parenthetical_does_not_extend_label_geometry() -> None:
    spec = _spec()
    spec["parent"]["aliases"] = ["Tiền gửi và cho vay các TCTD khác"]
    spec["children"][0]["aliases"] = ["Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành"]
    spec["children"][1]["aliases"] = ["Cho vay TCTD khác"]
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(
                    3,
                    "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
                    "",
                    [50, 100, 520, 122],
                ),
                _line(4, "(2025)", "", [50, 122, 130, 144]),
                _line(5, "100", "100", [600, 122, 700, 144]),
                _line(6, "90", "90", [800, 122, 900, 144]),
                _line(7, "Cho vay TCTD khác", "", [50, 175, 300, 197]),
                _line(8, "20", "20", [600, 175, 700, 197]),
                _line(9, "10", "10", [800, 175, 900, 197]),
            ]
        )
    ]

    result = build_accounting_family_row_axis_v1(pages, spec)

    row = next(item for item in result["rows"] if item["role"] == "SHORT_TERM")
    assert row["values"] == []
    assert row["missing_column_ordinals"] == [0, 1]


def test_repeated_body_columns_reject_one_same_row_audit_stamp_number() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"].insert(
        9,
        _line(11, "5", "5", [950, 150, 990, 172]),
    )
    for ordinal, line in enumerate(pages[0]["lines"]):
        line["line_ordinal"] = ordinal

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["metrics"]["bound_value_count"] == 4
    assert result["metrics"]["complete_trailing_value_row_count"] == 1
    assert result["metrics"]["partial_trailing_value_row_count"] == 0
    medium = result["rows"][1]
    assert [value["raw_prediction"] for value in medium["values"]] == ["200", "180"]
    assert all(value["sample_id"] != "sample-000000012" for value in medium["values"])
    assert [value["raw_prediction"] for value in result["trailing_value_rows"][0]["values"]] == [
        "300",
        "270",
    ]


def test_adjacent_rows_cannot_consume_the_same_source_cell_twice() -> None:
    pages = _ordinary_pages()
    # Remove MEDIUM current and place SHORT current low enough that it weakly
    # overlaps MEDIUM too.  Per-row assignment alone would duplicate `100`.
    pages[0]["lines"][4]["bbox"] = [600, 116, 700, 144]
    pages[0]["lines"][7]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }

    result = build_accounting_family_row_axis_v1(pages, _spec())

    short, medium = result["rows"]
    assert [value["raw_prediction"] for value in short["values"]] == ["100", "90"]
    assert [value["raw_prediction"] for value in medium["values"]] == ["180"]
    assert medium["missing_column_ordinals"] == [0]
    assert medium["status"] == "PARTIAL_VISIBLE_VALUE_LANES_REQUIRES_PIXEL_RESCUE"
    used = [value["sample_id"] for row in result["rows"] for value in row["values"]]
    assert len(used) == len(set(used))


def test_adjacent_row_exclusivity_is_reused_by_visible_dash_rescue() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][4]["bbox"] = [600, 116, 700, 144]
    pages[0]["lines"][7]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    base = build_accounting_family_row_axis_v1(pages, _spec())
    medium = base["rows"][1]
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], medium)
    label = medium["label_match"]
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][label["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    proposal = next(item for item in proposals if item["column_ordinal"] == 0)

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=(
            {
                "column_ordinal": 0,
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"]),
                "role": "MEDIUM_TERM",
            },
        ),
    )

    short, medium = result["rows"]
    assert [value["raw_prediction"] for value in short["values"]] == ["100", "90"]
    assert [value["raw_prediction"] for value in medium["values"]] == ["-", "180"]
    assert result["metrics"]["visible_dash_zero_count"] == 1


def test_multiple_dash_rescues_replay_against_one_immutable_base_grid() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][4]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    pages[0]["lines"][8]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    base = build_accounting_family_row_axis_v1(pages, _spec())
    rescues: list[dict[str, object]] = []
    for row, lane in zip(base["rows"], (0, 1), strict=True):
        centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], row)
        label = row["label_match"]
        proposals = propose_missing_value_lane_regions_v1(
            [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
            label_boxes=[pages[0]["lines"][label["source_line_index"]]["bbox"]],
            is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
            page_width=1000,
            page_height=1200,
            resolved_column_centers=centers,
            resolved_visible_value_cells=visible_cells,
        )
        proposal = next(item for item in proposals if item["column_ordinal"] == lane)
        rescues.append(
            {
                "column_ordinal": lane,
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"]),
                "role": row["role"],
            }
        )

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=tuple(rescues),
    )

    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["metrics"]["visible_dash_rescue_attempt_count"] == 2
    assert result["metrics"]["visible_dash_zero_count"] == 2
    assert [row["missing_column_ordinals"] for row in result["rows"]] == [[], []]
    assert [
        value["parsed_token"]["classification"]
        for row in result["rows"]
        for value in row["values"]
        if value["raw_prediction"] == "-"
    ] == ["DASH_ZERO", "DASH_ZERO"]


def test_degraded_short_mark_requires_clear_same_row_peer() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][4]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    pages[0]["lines"][5]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    base = build_accounting_family_row_axis_v1(pages, _spec())
    row = base["rows"][0]
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], row)
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][row["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    by_lane = {item["column_ordinal"]: item for item in proposals}
    rescues = (
        {
            "column_ordinal": 0,
            "page_sequence": 1,
            "region": _dash_region(by_lane[0]["raw_pixel_bbox"], degraded_short_mark=True),
            "role": "SHORT_TERM",
        },
        {
            "column_ordinal": 1,
            "page_sequence": 1,
            "region": _dash_region(by_lane[1]["raw_pixel_bbox"]),
            "role": "SHORT_TERM",
        },
    )

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=rescues,
    )

    short = result["rows"][0]
    assert [value["raw_prediction"] for value in short["values"]] == ["-", "-"]
    assert result["metrics"]["visible_dash_zero_count"] == 2
    degraded = result["visible_dash_rescues"][0]
    assert degraded["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    assert degraded["supporting_peer_dash_column_ordinal"] == 1


def test_degraded_short_mark_without_clear_peer_stays_unresolved() -> None:
    pages = _ordinary_pages()
    pages[0]["lines"][4]["numeric_recognition"] = {
        "raw_prediction": "",
        "reader_score": 0.2,
    }
    base = build_accounting_family_row_axis_v1(pages, _spec())
    row = base["rows"][0]
    centers, visible_cells = row_axis_v1._resolved_page_grid_inputs(base["rows"], row)
    proposals = propose_missing_value_lane_regions_v1(
        [{**line, "source_line_index": line["line_ordinal"]} for line in pages[0]["lines"]],
        label_boxes=[pages[0]["lines"][row["label_match"]["source_line_index"]]["bbox"]],
        is_numeric=lambda line: line["numeric_recognition"]["raw_prediction"].isdigit(),
        page_width=1000,
        page_height=1200,
        resolved_column_centers=centers,
        resolved_visible_value_cells=visible_cells,
    )
    proposal = next(item for item in proposals if item["column_ordinal"] == 0)

    result = build_accounting_family_row_axis_v1(
        pages,
        _spec(),
        visible_dash_rescues=(
            {
                "column_ordinal": 0,
                "page_sequence": 1,
                "region": _dash_region(proposal["raw_pixel_bbox"], degraded_short_mark=True),
                "role": "SHORT_TERM",
            },
        ),
    )

    short = result["rows"][0]
    assert short["missing_column_ordinals"] == [0]
    assert result["metrics"]["visible_dash_zero_count"] == 0
    degraded = result["visible_dash_rescues"][0]
    assert degraded["classification"] == "DEGRADED_CENTERED_SHORT_MARK_CANDIDATE"
    assert degraded["supporting_peer_dash_column_ordinal"] is None


def test_family_rows_continue_across_pages_without_joining_label_text() -> None:
    pages = [
        _page(
            [
                _line(0, "Phân tích dư nợ theo thời gian", "", [30, 20, 430, 42]),
                _line(1, "Nợ ngắn hạn", "", [50, 100, 300, 122]),
                _line(2, "100", "100", [600, 100, 700, 122]),
                _line(3, "90", "90", [800, 100, 900, 122]),
            ],
            page_sequence=1,
        ),
        _page(
            [
                _line(0, "Nợ trung hạn", "", [50, 100, 300, 122], page=2),
                _line(1, "200", "200", [600, 100, 700, 122], page=2),
                _line(2, "180", "180", [800, 100, 900, 122], page=2),
                _line(3, "300", "300", [600, 150, 700, 172], page=2),
                _line(4, "270", "270", [800, 150, 900, 172], page=2),
            ],
            page_sequence=2,
        ),
    ]

    result = build_accounting_family_row_axis_v1(pages, _spec())

    assert result["topology_status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert [row["label_match"]["page_sequence"] for row in result["rows"]] == [1, 2]
    assert [value["page_sequence"] for value in result["rows"][1]["values"]] == [2, 2]
    assert result["trailing_value_rows"][0]["page_sequence"] == 2


def test_one_exact_region_can_be_bound_for_downstream_disambiguation() -> None:
    spec = copy.deepcopy(_contextual_summary_spec())
    spec["children"][1]["matchers"].append({"aliases": ["Tiền gửi bằng VND"], "within_role": None})
    spec["required_role_combinations"].append(["DEPOSIT_VND", "LOAN_GROUP"])
    pages = [
        _page(
            [
                _line(0, "Tiền gửi và cho vay các TCTD khác", "", [30, 20, 430, 42]),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _line(3, "Tiền gửi tại TCTD khác", "", [50, 100, 300, 122]),
                _line(4, "100", "100", [600, 100, 700, 122]),
                _line(5, "90", "90", [800, 100, 900, 122]),
                _line(6, "Cho vay TCTD khác", "", [50, 150, 300, 172]),
                _line(7, "20", "20", [600, 150, 700, 172]),
                _line(8, "10", "10", [800, 150, 900, 172]),
            ],
            page_sequence=1,
        ),
        _page(
            [
                _line(
                    0,
                    "Tiền gửi và cho vay các TCTD khác",
                    "",
                    [30, 20, 430, 42],
                    page=2,
                ),
                _line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72], page=2),
                _line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72], page=2),
                _line(3, "Tiền gửi bằng VND", "", [50, 130, 300, 152], page=2),
                _line(4, "Ghi chú", "", [80, 160, 300, 182], page=2),
                _line(5, "100", "100", [600, 130, 700, 152], page=2),
                _line(6, "90", "90", [800, 130, 900, 152], page=2),
                _line(7, "Cho vay TCTD khác", "", [50, 190, 300, 212], page=2),
                _line(8, "Bằng VND", "", [80, 230, 300, 252], page=2),
                _line(9, "20", "20", [600, 230, 700, 252], page=2),
                _line(10, "10", "10", [800, 230, 900, 252], page=2),
            ],
            page_sequence=2,
        ),
    ]
    topology = row_axis_v1.topology_v1.build_accounting_family_topology_scan_v1(
        row_axis_v1._topology_pages(row_axis_v1._pages(pages)),
        spec,
    )
    assert topology["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    assert build_accounting_family_row_axis_v1(pages, spec)["rows"] == []

    candidates = [
        build_accounting_family_row_axis_for_topology_region_v1(
            pages,
            spec,
            region,
        )
        for region in topology["regions"]
    ]

    assert [candidate["topology_region"]["page_sequence"] for candidate in candidates] == [1, 2]
    assert [row["role"] for row in candidates[0]["rows"]] == [
        "DEPOSIT_GROUP",
        "LOAN_GROUP",
    ]
    assert [row["role"] for row in candidates[1]["rows"]] == ["DEPOSIT_VND", "LOAN_VND"]
    assert (
        validate_accounting_family_row_axis_replay_v1(candidates[1], pages, spec) == candidates[1]
    )


def test_noncandidate_pages_need_no_render_width_but_matched_pages_do() -> None:
    pages = _ordinary_pages()
    pages.append(
        {
            "lines": [
                _line(0, "Thuyết minh khác", "", [30, 20, 430, 42], page=2),
            ],
            "page_sequence": 2,
            "page_width": None,
        }
    )

    result = build_accounting_family_row_axis_v1(pages, _spec())
    assert result["topology_status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"

    pages[0]["page_width"] = None
    with pytest.raises(AccountingFamilyRowAxisV1Error, match="authenticated render width"):
        build_accounting_family_row_axis_v1(pages, _spec())


def test_authenticated_same_turn_topology_seam_avoids_full_rescan(monkeypatch) -> None:
    pages = _ordinary_pages()
    spec = _spec()
    topology = row_axis_v1.topology_v1.build_accounting_family_topology_scan_v1(
        row_axis_v1._topology_pages(row_axis_v1._pages(pages)), spec
    )
    monkeypatch.setattr(
        row_axis_v1.topology_v1,
        "build_accounting_family_topology_scan_v1",
        lambda *_args, **_kwargs: pytest.fail("same-turn row axis rescanned the full document"),
    )

    result = row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
        pages, spec, topology, topology["regions"][0]
    )

    assert result["topology_scan_id"] == topology["scan_id"]
    assert [row["role"] for row in result["rows"]] == ["SHORT_TERM", "MEDIUM_TERM"]

    forged = copy.deepcopy(topology)
    forged["status"] = "UNRESOLVED_NO_COMPLETE_REGION"
    with pytest.raises(AccountingFamilyRowAxisV1Error, match="topology input drifted"):
        row_axis_v1._build_accounting_family_row_axis_from_authenticated_topology_scan_v1(
            pages, spec, forged, topology["regions"][0]
        )


def test_exact_replay_rejects_coordinated_value_mutation_and_types() -> None:
    pages = _ordinary_pages()
    result = build_accounting_family_row_axis_v1(pages, _spec())
    forged = copy.deepcopy(result)
    forged["rows"][0]["values"][0]["raw_prediction"] = "999"
    material = copy.deepcopy(forged)
    material.pop("row_axis_id")
    forged["row_axis_id"] = "afrav1:axis:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingFamilyRowAxisV1Error, match="replay exactly"):
        validate_accounting_family_row_axis_replay_v1(forged, pages, _spec())
    malformed = _ordinary_pages()
    malformed[0]["lines"][4]["numeric_recognition"]["reader_score"] = True
    with pytest.raises(AccountingFamilyRowAxisV1Error, match="identity/text/score"):
        build_accounting_family_row_axis_v1(malformed, _spec())
