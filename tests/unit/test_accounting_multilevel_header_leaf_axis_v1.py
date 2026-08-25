from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_family_column_context_multilevel_v2 import (
    build_accounting_family_column_context_multilevel_v2,
)
from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.evaluation.accounting_multilevel_header_leaf_axis_v1 import (
    AccountingMultilevelHeaderLeafAxisV1Error,
    build_accounting_multilevel_header_leaf_axis_v1,
    validate_accounting_multilevel_header_leaf_axis_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_CENTERS = [200.0, 400.0, 600.0, 800.0]
_KINDS = ["MONEY", "PERCENT", "MONEY", "PERCENT"]


def _context() -> dict[str, object]:
    return {
        "balance_comparative_period_end": "31/12/2024",
        "current_period_end": "31/12/2025",
        "current_period_start": "01/01/2025",
        "flow_comparative_period_end": "31/12/2024",
        "flow_comparative_period_start": "01/01/2024",
        "observed_dates": [],
        "period_kind": "ANNUAL",
        "reporting_year": 2025,
        "resolution": "DOMINANT_REPEATED_FULL_DATE_CONSENSUS",
        "supporting_page_count": 2,
    }


def _header_line(
    index: int,
    text: str,
    bbox: list[int],
    **extra: object,
) -> dict[str, object]:
    return {
        "bbox": bbox,
        "source_line_index": index,
        "vietocr_text": text,
        **extra,
    }


def _headers(*, semantic_money: bool = False) -> list[dict[str, object]]:
    money = "Giá trị" if semantic_money else "triệu đồng"
    lines = [
        _header_line(10, "31/12/2025", [150, 20, 450, 45]),
        _header_line(11, "31/12/2024", [550, 20, 850, 45]),
        _header_line(12, money, [150, 55, 250, 80]),
        _header_line(13, "%", [350, 55, 450, 80]),
        _header_line(14, money, [550, 55, 650, 80]),
        _header_line(15, "%", [750, 55, 850, 80]),
    ]
    if semantic_money:
        lines.insert(0, _header_line(9, "Đơn vị: triệu đồng", [150, 1, 850, 16]))
    return lines


def _build(headers: list[dict[str, object]]) -> dict[str, object]:
    return build_accounting_multilevel_header_leaf_axis_v1(
        headers,
        column_centers=_CENTERS,
        page_width=1000,
        document_period_context=_context(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_kinds=_KINDS,
    )


def _split_vietnamese_date_headers() -> list[dict[str, object]]:
    return [
        _header_line(27, "Ngày 31 tháng 12", [790, 826, 1012, 860]),
        _header_line(28, "Ngày 31 tháng 12", [1159, 824, 1376, 858]),
        _header_line(29, "năm 2025", [879, 860, 1014, 894]),
        _header_line(30, "năm 2024", [1248, 860, 1376, 894]),
        _header_line(31, "(Trình bày lại)", [1199, 892, 1373, 928]),
        _header_line(32, "Triệu đồng", [874, 931, 1014, 967]),
        _header_line(33, "%", [1078, 931, 1120, 965]),
        _header_line(34, "Triệu đồng", [1240, 931, 1376, 965]),
        _header_line(35, "%", [1435, 928, 1477, 962]),
    ]


def _build_split_vietnamese_date_header(
    headers: list[dict[str, object]],
) -> dict[str, object]:
    return build_accounting_multilevel_header_leaf_axis_v1(
        headers,
        column_centers=[957.5, 1084.5, 1330.0, 1442.25],
        page_width=1623,
        document_period_context=_context(),
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_kinds=_KINDS,
    )


def test_two_period_parents_project_to_four_typed_header_leaves() -> None:
    result = _build(_headers())

    assert result["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["unresolved_reasons"] == []
    assert [leaf["lane_kind"] for leaf in result["leaf_axis"]] == _KINDS
    assert [leaf["resolved_period"] for leaf in result["leaf_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]
    assert [
        (leaf["period_parent_column_start"], leaf["period_parent_column_stop"])
        for leaf in result["leaf_axis"]
    ] == [(0, 2), (0, 2), (2, 4), (2, 4)]
    assert result["header_graph"]["format_version"] == (
        "ADAPTIVE_ACCOUNTING_MULTILEVEL_HEADER_GRAPH_V1"
    )


def test_narrow_period_headers_can_anchor_two_identical_typed_leaf_groups() -> None:
    headers = _headers()
    headers[0]["bbox"] = [150, 20, 250, 45]
    headers[1]["bbox"] = [550, 20, 650, 45]

    result = _build(headers)

    assert result["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["period_resolution_mode"].endswith(
        "_REPEATED_TYPED_LEAF_SEQUENCE_LEADING_ANCHOR_PARTITION"
    )
    assert [
        (leaf["period_parent_column_start"], leaf["period_parent_column_stop"])
        for leaf in result["leaf_axis"]
    ] == [(0, 2), (0, 2), (2, 4), (2, 4)]
    assert (
        validate_accounting_multilevel_header_leaf_axis_replay_v1(
            result,
            headers,
            column_centers=_CENTERS,
            page_width=1000,
            document_period_context=_context(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_kinds=_KINDS,
        )
        == result
    )

    forged = copy.deepcopy(result)
    forged["leaf_axis"][1]["period_parent_column_stop"] = 3
    material = copy.deepcopy(forged)
    material.pop("axis_id")
    forged["axis_id"] = "amhlav1:axis:" + canonical_json_sha256_v1(material)
    with pytest.raises(AccountingMultilevelHeaderLeafAxisV1Error):
        validate_accounting_multilevel_header_leaf_axis_replay_v1(
            forged,
            headers,
            column_centers=_CENTERS,
            page_width=1000,
            document_period_context=_context(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_kinds=_KINDS,
        )


def test_split_vietnamese_date_fragments_use_exact_intersection_and_repeated_leaf_groups() -> None:
    headers = _split_vietnamese_date_headers()
    result = _build_split_vietnamese_date_header(headers)

    assert result["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
    assert result["period_resolution_mode"].endswith(
        "_INTERSECTING_SPLIT_FRAGMENT_ANCHOR_REPEATED_TYPED_LEAF_SEQUENCE_LEADING_ANCHOR_PARTITION"
    )
    assert [leaf["resolved_period"] for leaf in result["leaf_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]
    assert [leaf["period_evidence_source_line_indices"] for leaf in result["leaf_axis"]] == [
        [27, 29],
        [27, 29],
        [28, 30],
        [28, 30],
    ]
    assert (
        validate_accounting_multilevel_header_leaf_axis_replay_v1(
            result,
            headers,
            column_centers=[957.5, 1084.5, 1330.0, 1442.25],
            page_width=1623,
            document_period_context=_context(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_kinds=_KINDS,
        )
        == result
    )


@pytest.mark.parametrize(
    "mutation", ["disjoint_fragment", "same_level_fragment", "all_low_confidence"]
)
def test_split_period_fragments_require_one_connected_exact_leading_lane_anchor(
    mutation: str,
) -> None:
    headers = _split_vietnamese_date_headers()
    if mutation == "disjoint_fragment":
        headers[3]["bbox"] = [879, 860, 1014, 894]
    elif mutation == "same_level_fragment":
        headers[3]["bbox"] = [1248, 824, 1376, 858]
    else:
        headers[2]["bbox"] = [790, 860, 1012, 894]

    result = _build_split_vietnamese_date_header(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []


def test_narrow_period_header_not_anchored_to_group_start_stays_unresolved() -> None:
    headers = _headers()
    headers[0]["bbox"] = [150, 20, 250, 45]
    headers[1]["bbox"] = [750, 20, 850, 45]

    result = _build(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []


def test_visual_canonicalization_is_provider_order_invariant() -> None:
    headers = _headers()
    expected = _build(headers)

    assert _build(list(reversed(headers))) == expected


def test_semantic_money_leaf_does_not_invent_currency_or_scale() -> None:
    result = _build(_headers(semantic_money=True))

    assert result["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
    money = [leaf for leaf in result["leaf_axis"] if leaf["lane_kind"] == "MONEY"]
    assert {leaf["lane_kind_resolution"] for leaf in money} == {"EXACT_SEMANTIC_MONEY_HEADER"}
    assert all("currency" not in leaf and "magnitude_power10" not in leaf for leaf in money)
    assert result["safety"]["currency_or_magnitude_inferred_from_money_lane_kind"] is False


def test_period_parents_with_a_gap_do_not_form_a_partition() -> None:
    headers = _headers(semantic_money=True)
    headers[1]["bbox"] = [150, 20, 250, 45]
    headers[2]["bbox"] = [750, 20, 850, 45]

    result = _build(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []
    assert "PERIOD_PARENTS_DO_NOT_EXACTLY_PARTITION_BODY_COLUMNS" in result["unresolved_reasons"]


def test_duplicate_period_or_leaf_kind_evidence_fails_closed() -> None:
    duplicate_period = _headers()
    duplicate_period[1]["vietocr_text"] = "31/12/2025"
    period_result = _build(duplicate_period)
    assert period_result["leaf_axis"] == []
    assert (
        "VISIBLE_PERIOD_PARENTS_DIFFER_FROM_DOCUMENT_BALANCE_PERIODS"
        in period_result["unresolved_reasons"]
    )

    duplicate_leaf = _headers()
    duplicate_leaf.append(_header_line(16, "Số tiền", [150, 84, 250, 105]))
    leaf_result = _build(duplicate_leaf)
    assert leaf_result["leaf_axis"] == []
    assert (
        "EACH_BODY_COLUMN_REQUIRES_ONE_UNAMBIGUOUS_TYPED_HEADER_LEAF"
        in leaf_result["unresolved_reasons"]
    )


def test_merged_periods_without_word_boxes_remain_unresolved() -> None:
    headers = _headers()[2:]
    headers.insert(
        0,
        _header_line(
            10,
            "31/12/2025 31/12/2024",
            [150, 20, 850, 45],
            tokens=["31/12/2025", "31/12/2024"],
        ),
    )

    result = _build(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []
    assert (
        "MERGED_PERIOD_OR_LEAF_HEADER_WITHOUT_WORD_BOXES_UNRESOLVED" in result["unresolved_reasons"]
    )


def test_merged_period_surface_without_tokens_remains_unresolved() -> None:
    headers = _headers()
    headers[0]["vietocr_text"] = "31/12/2025 31/12/2024"

    result = _build(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []
    assert (
        "MERGED_PERIOD_OR_LEAF_HEADER_WITHOUT_WORD_BOXES_UNRESOLVED" in result["unresolved_reasons"]
    )


def test_word_boxes_covering_only_one_of_two_visible_periods_remain_unresolved() -> None:
    headers = _headers()
    headers[0].update(
        {
            "token_bboxes": [[150, 20, 450, 45]],
            "tokens": ["31/12/2025"],
            "vietocr_text": "31/12/2025 31/12/2024",
        }
    )

    result = _build(headers)

    assert result["status"] == "UNRESOLVED_MULTILEVEL_HEADER_LEAF_AXIS"
    assert result["leaf_axis"] == []
    assert (
        "MERGED_PERIOD_OR_LEAF_HEADER_WITHOUT_WORD_BOXES_UNRESOLVED" in result["unresolved_reasons"]
    )


def test_merged_period_word_boxes_can_prove_the_parent_partition() -> None:
    headers = _headers()[2:]
    headers.insert(
        0,
        _header_line(
            10,
            "31/12/2025 31/12/2024",
            [150, 20, 850, 45],
            tokens=["31/12/2025", "31/12/2024"],
            token_bboxes=[[150, 20, 450, 45], [550, 20, 850, 45]],
        ),
    )

    result = _build(headers)

    assert result["status"] == "MULTILEVEL_HEADER_LEAF_AXIS_BOUND_PROPOSAL_ONLY"
    assert [leaf["resolved_period"] for leaf in result["leaf_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]


def test_exact_replay_rejects_a_self_rehashed_period_mutation() -> None:
    headers = _headers()
    result = _build(headers)
    forged = copy.deepcopy(result)
    forged["leaf_axis"][0]["resolved_period"] = "31/12/2099"
    material = copy.deepcopy(forged)
    material.pop("axis_id")
    forged["axis_id"] = "amhlav1:axis:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingMultilevelHeaderLeafAxisV1Error, match="replay exactly"):
        validate_accounting_multilevel_header_leaf_axis_replay_v1(
            forged,
            headers,
            column_centers=_CENTERS,
            page_width=1000,
            document_period_context=_context(),
            period_semantics="BALANCE_COMPARATIVE",
            expected_lane_kinds=_KINDS,
        )


def _topology_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Doanh nghiệp nhà nước"],
                "presence": "REQUIRED",
                "role": "STATE_ENTERPRISE",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Công ty TNHH"],
                "presence": "REQUIRED",
                "role": "LIMITED_COMPANY",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "GENERIC_ENTERPRISE_TYPE",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Tiền gửi của khách hàng"],
        "limits": {
            "max_cluster_span_lines": 40,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Theo loại hình doanh nghiệp"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "ENTERPRISE_TYPE",
        },
        "structural_reset_aliases": ["Phân tích theo ngành nghề"],
    }


def _page_line(
    ordinal: int,
    text: str,
    numeric: str,
    bbox: list[int],
    *,
    page: int,
) -> dict[str, object]:
    sample = page * 100 + ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/header-leaf-{sample:04d}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": sample + 100,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"header-leaf-sample-{sample:06d}",
        "vietocr_text": text,
    }


def _column_context_pages() -> list[dict[str, object]]:
    page_one_surfaces = [
        ("Theo loại hình doanh nghiệp", "", [20, 20, 430, 42]),
        ("Đơn vị: Triệu đồng", "", [480, 48, 920, 66]),
        ("31/12/2025", "", [480, 70, 680, 92]),
        ("31/12/2024", "", [720, 70, 920, 92]),
        ("Giá trị", "", [480, 98, 560, 120]),
        ("%", "", [600, 98, 680, 120]),
        ("Giá trị", "", [720, 98, 800, 120]),
        ("%", "", [840, 98, 920, 120]),
        ("Doanh nghiệp nhà nước", "", [40, 145, 360, 167]),
        ("100", "100", [480, 145, 560, 167]),
        ("60", "60", [600, 145, 680, 167]),
        ("90", "90", [720, 145, 800, 167]),
        ("55", "55", [840, 145, 920, 167]),
        ("Công ty TNHH", "", [40, 190, 360, 212]),
        ("200", "200", [480, 190, 560, 212]),
        ("40", "40", [600, 190, 680, 212]),
        ("180", "180", [720, 190, 800, 212]),
        ("45", "45", [840, 190, 920, 212]),
    ]
    page_two_surfaces = [
        ("31/12/2025", "", [480, 20, 680, 42]),
        ("31/12/2024", "", [720, 20, 920, 42]),
        ("Đơn vị: Triệu đồng", "", [480, 48, 920, 70]),
        ("Phân tích theo ngành nghề", "", [20, 100, 430, 122]),
    ]
    return [
        {
            "lines": [
                _page_line(ordinal, text, numeric, bbox, page=1)
                for ordinal, (text, numeric, bbox) in enumerate(page_one_surfaces)
            ],
            "page_sequence": 1,
            "page_width": 1000,
        },
        {
            "lines": [
                _page_line(ordinal, text, numeric, bbox, page=2)
                for ordinal, (text, numeric, bbox) in enumerate(page_two_surfaces)
            ],
            "page_sequence": 2,
            "page_width": 1000,
        },
    ]


def test_family_column_context_uses_multilevel_leaf_axis_for_mixed_lanes() -> None:
    pages = _column_context_pages()
    spec = _topology_spec()
    row_axis = build_accounting_family_row_axis_v1(pages, spec)

    result = build_accounting_family_column_context_multilevel_v2(
        row_axis,
        pages,
        spec,
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    assert result["status"] == "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY"
    assert [item["resolved_period"] for item in result["period_axis"]] == [
        "31/12/2025",
        "31/12/2025",
        "31/12/2024",
        "31/12/2024",
    ]
    assert [item["unit_kind"] for item in result["unit_axis"]] == _KINDS
    assert [item["magnitude_power10"] for item in result["unit_axis"]] == [6, None, 6, None]
    assert all(
        "MULTILEVEL_PERIOD_PARENT_PROPAGATED_TO_HEADER_LEAF" in item["projection_status"]
        for item in result["period_axis"]
    )


def test_explicit_money_leaf_conflicting_with_shared_table_unit_fails_closed() -> None:
    pages = _column_context_pages()
    pages[0]["lines"][4]["vietocr_text"] = "Tỷ đồng"
    spec = _topology_spec()
    row_axis = build_accounting_family_row_axis_v1(pages, spec)

    result = build_accounting_family_column_context_multilevel_v2(
        row_axis,
        pages,
        spec,
        period_semantics="BALANCE_COMPARATIVE",
        expected_lane_unit_kinds=_KINDS,
    )

    assert result["status"] == "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
    assert result["unit_axis"] == []
    assert "UNIT_AXIS_NOT_BOUND_TO_EVERY_BODY_COLUMN" in result["unresolved_reasons"]
