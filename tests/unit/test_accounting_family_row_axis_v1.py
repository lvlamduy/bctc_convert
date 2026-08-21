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


def _dash_region(raw_pixel_bbox: list[int]) -> dict[str, object]:
    image = Image.new("RGB", (42, 27), "white")
    ImageDraw.Draw(image).rectangle((16, 11, 25, 15), fill="black")
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
