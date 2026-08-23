from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_type_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_type_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
loan_type = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = loan_type
_SPEC.loader.exec_module(loan_type)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 120, y + 24],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _direct(*, reordered: bool = False, missing_dash: bool = False) -> list[tuple[str, int, int]]:
    rows = [
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", "100", "90"),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", "10", "9"),
        ("Cho thuê tài chính", "5", "4"),
        ("Các khoản trả thay khách hàng", "3", "2"),
        ("Cho vay bằng vốn tài trợ, ủy thác đầu tư", "2", "1"),
    ]
    if reordered:
        rows = [rows[0], rows[4], rows[1], rows[3], rows[2]]
    result: list[tuple[str, int, int]] = [
        ("5. CHO VAY KHÁCH HÀNG", 0, 0),
        ("30/06/2026", 500, 40),
        ("31/12/2025", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
    ]
    for row_index, (label, current, previous) in enumerate(rows):
        y = 120 + row_index * 45
        result.append((label, 0, y))
        if not (missing_dash and "ủy thác" in label):
            result.extend([(current, 500, y), (previous, 800, y)])
    current_total = sum(int(row[1]) for row in rows) - (2 if missing_dash else 0)
    previous_total = sum(int(row[2]) for row in rows) - (1 if missing_dash else 0)
    result.extend(
        [
            (str(current_total), 500, 120 + len(rows) * 45),
            (str(previous_total), 800, 120 + len(rows) * 45),
            ("Phân tích chất lượng nợ cho vay", 0, 400),
        ]
    )
    return result


def _subtotal_margin() -> list[tuple[str, int, int]]:
    result = _direct()[:-3]
    result.extend(
        [
            ("120", 500, 345),
            ("106", 800, 345),
            ("Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS", 0, 390),
            ("5", 500, 390),
            ("4", 800, 390),
            ("125", 500, 435),
            ("110", 800, 435),
            ("Phân tích chất lượng nợ cho vay", 0, 480),
        ]
    )
    return result


def _percent_lanes() -> list[tuple[str, int, int]]:
    rows = [
        ("Cho vay các tổ chức kinh tế và cá nhân trong nước", "90", "90", "80", "80"),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", "5", "5", "10", "10"),
        ("Các khoản trả thay khách hàng", "3", "3", "4", "4"),
        ("Cấp tín dụng khác", "2", "2", "6", "6"),
    ]
    result: list[tuple[str, int, int]] = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Ngày 31 tháng 3 năm 2026", 400, 35),
        ("Ngày 31 tháng 12 năm 2025", 900, 35),
        ("Triệu đồng", 400, 70),
        ("%", 600, 70),
        ("Triệu đồng", 900, 70),
        ("%", 1100, 70),
    ]
    for offset, row in enumerate(rows):
        y = 120 + offset * 50
        result.append((row[0], 0, y))
        result.extend(
            [
                (row[1], 400, y),
                (row[2], 600, y),
                (row[3], 900, y),
                (row[4], 1100, y),
            ]
        )
    result.extend(
        [
            ("100", 400, 330),
            ("100", 600, 330),
            ("100", 900, 330),
            ("100", 1100, 330),
            ("10.1", 0, 375),
            ("Phân tích chất lượng nợ cho vay", 0, 410),
        ]
    )
    return result


def test_direct_total_accepts_reordered_children_without_bank_routing() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_direct(reordered=True))])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "ENTRUSTED_OR_SPONSORED_CAPITAL",
        "DISCOUNT_INSTRUMENTS",
        "PAYMENTS_ON_BEHALF",
        "FINANCIAL_LEASE",
    ]
    assert graph["layout_mode"] == "TWO_MONEY_LANES"
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )
    assert result["safety"]["bank_filename_note_or_page_used_for_inference"] is False


def test_owner_plus_two_children_can_be_unique_when_axes_total_and_closure_agree() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", 0, 165),
        ("10", 500, 165),
        ("9", 800, 165),
        ("110", 500, 210),
        ("99", 800, 210),
        ("Phân tích chất lượng nợ cho vay", 0, 255),
    ]
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "DISCOUNT_INSTRUMENTS",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_missing_dash_cells_are_not_imputed_as_zero() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(_direct(missing_dash=True))]
    )

    graph = result["graphs"][0]
    entrusted = next(
        row for row in graph["rows"] if row["role"] == "ENTRUSTED_OR_SPONSORED_CAPITAL"
    )
    assert [value["status"] for value in entrusted["values"]] == [
        "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
        "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
    ]
    assert all(
        check["status"] == "UNRESOLVED_MISSING_SEMANTIC_CELL_NOT_IMPUTED"
        for check in graph["accounting_checks"]
    )


def test_core_subtotal_then_margin_then_grand_total_is_one_generic_variant() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_subtotal_margin())])

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert len(graph["intermediate_totals"]) == 1
    assert [item["semantic_surface"] for item in graph["intermediate_totals"][0]] == [
        "120",
        "106",
    ]
    assert [item["semantic_surface"] for item in graph["total"]] == ["125", "110"]
    assert graph["rows"][-1]["role"] == "MARGIN_AND_SECURITIES_ADVANCE"


def test_money_percent_companion_lanes_and_broad_other_credit_are_preserved() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_percent_lanes())])

    graph = result["graphs"][0]
    assert graph["lane_types"] == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert graph["layout_mode"] == "MONEY_PERCENT_COMPANION_LANES"
    assert graph["rows"][-1]["role"] == "UNMAPPED_OTHER_CREDIT"
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_wrapped_label_may_be_interleaved_with_numeric_geometry() -> None:
    surfaces = _direct()
    discount = next(
        index for index, item in enumerate(surfaces) if item[0].startswith("Cho vay chiết khấu")
    )
    _label, _x, y = surfaces[discount]
    surfaces[discount : discount + 3] = [
        ("Cho vay chiết khấu công cụ chuyển nhượng và", 0, y),
        ("10", 500, y),
        ("9", 800, y),
        ("các giấy tờ có giá", 0, y + 18),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    graph = result["graphs"][0]
    discount_row = next(row for row in graph["rows"] if row["role"] == "DISCOUNT_INSTRUMENTS")
    assert discount_row["label"]["source_line_indices"] == [8, 11]
    assert [item["semantic_surface"] for item in discount_row["values"]] == ["10", "9"]


def test_wrapped_labels_follow_visual_order_when_provider_indices_are_interleaved() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và", 0, 165),
        ("10", 500, 165),
        ("9", 800, 165),
        ("Cho thuê tài chính", 0, 220),
        ("5", 500, 220),
        ("4", 800, 220),
        ("%nc", 1600, 174),
        # Some providers emit this wrapped continuation after the next row in
        # their source array even though its pixel y-position is still above it.
        ("các giấy tờ có giá", 0, 183),
        ("115", 500, 265),
        ("103", 800, 265),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    discount = next(row for row in graph["rows"] if row["role"] == "DISCOUNT_INSTRUMENTS")
    assert discount["label"]["source_line_indices"] == [8, 15]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "DISCOUNT_INSTRUMENTS",
        "FINANCIAL_LEASE",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_long_label_allows_bounded_added_token_only_inside_complete_topology() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay đối với các tổ chức kinh tế, cá nhân nước ngoài", 0, 165),
        ("6", 500, 165),
        ("5", 800, 165),
        ("106", 500, 210),
        ("95", 800, 210),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    foreign = next(
        row
        for row in result["graphs"][0]["rows"]
        if row["role"] == "FOREIGN_ORGANIZATIONS_INDIVIDUALS"
    )
    assert (
        foreign["label"]["match_kind"]
        == "HIGH_SIMILARITY_ACCENTLESS_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY"
    )


def test_row_cluster_alignment_handles_staggered_numeric_columns() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 112),
        ("90", 800, 105),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", 0, 165),
        ("10", 500, 157),
        ("9", 800, 150),
        ("Các khoản trả thay khách hàng", 0, 210),
        ("3", 500, 202),
        ("2", 800, 195),
        ("113", 500, 250),
        ("101", 800, 243),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    graph = result["graphs"][0]
    assert [[value["semantic_surface"] for value in row["values"]] for row in graph["rows"]] == [
        ["100", "90"],
        ["10", "9"],
        ["3", "2"],
    ]
    assert [item["semantic_surface"] for item in graph["total"]] == ["113", "101"]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_short_exact_alias_extends_to_its_wrapped_longer_alias() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế và cá nhân", 0, 120),
        ("trong nước", 0, 142),
        ("100", 500, 142),
        ("90", 800, 142),
        ("Các khoản trả thay khách hàng", 0, 180),
        ("3", 500, 180),
        ("2", 800, 180),
        ("103", 500, 220),
        ("92", 800, 220),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    graph = result["graphs"][0]
    assert graph["rows"][0]["label"]["surface"] == (
        "Cho vay các tổ chức kinh tế và cá nhân trong nước"
    )
    assert graph["rows"][0]["label"]["source_line_indices"] == [5, 6]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "PAYMENTS_ON_BEHALF",
    ]


def test_wrapped_label_uses_terminal_baseline_before_following_dash_row() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và", 0, 154),
        ("các giấy tờ có giá", 35, 192),
        ("10", 500, 192),
        ("9", 800, 192),
        ("Cho thuê tài chính", 0, 225),
        ("Các khoản trả thay khách hàng", 0, 264),
        ("3", 500, 264),
        ("2", 800, 264),
        ("113", 500, 310),
        ("101", 800, 310),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    rows = {row["role"]: row for row in result["graphs"][0]["rows"]}
    assert [item["semantic_surface"] for item in rows["DISCOUNT_INSTRUMENTS"]["values"]] == [
        "10",
        "9",
    ]
    assert [item["semantic_surface"] for item in rows["FINANCIAL_LEASE"]["values"]] == [
        None,
        None,
    ]


def test_long_visible_prefix_can_anchor_a_detector_dropped_continuation() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các", 0, 165),
        ("10", 500, 165),
        ("9", 800, 165),
        ("110", 500, 210),
        ("99", 800, 210),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    discount = next(
        row for row in result["graphs"][0]["rows"] if row["role"] == "DISCOUNT_INSTRUMENTS"
    )
    assert discount["label"]["match_kind"] == ("LONG_PREFIX_ANCHOR_IN_COMPLETE_TABLE_TOPOLOGY")


def test_ppocr_numeric_surface_retains_cell_when_vietocr_confuses_a_digit() -> None:
    page = _page(_direct(), primary_numeric_authority=True)
    confused = next(
        line for line in page["lines"] if line["vietocr_text"] == "10" and line["bbox"][0] == 500
    )
    confused["vietocr_text"] = "1O"
    assert confused["source_text"] == "10"

    result = loan_type.build_loan_type_variant_graph_document_v1([page])

    discount = next(
        row for row in result["graphs"][0]["rows"] if row["role"] == "DISCOUNT_INSTRUMENTS"
    )
    assert discount["values"][0]["source_line_index"] == confused["source_line_index"]
    assert discount["values"][0]["semantic_surface"] == "1O"


def test_wrong_family_and_insufficient_child_subset_remain_near_unresolved() -> None:
    page = _page(
        [
            ("Cho vay khách hàng", 0, 0),
            ("30/06/2026", 500, 40),
            ("31/12/2025", 800, 40),
            ("Triệu đồng", 500, 70),
            ("Triệu đồng", 800, 70),
            ("Nợ ngắn hạn", 0, 120),
            ("100", 500, 120),
            ("90", 800, 120),
            ("Nợ trung hạn", 0, 165),
            ("50", 500, 165),
            ("40", 800, 165),
            ("150", 500, 210),
            ("130", 800, 210),
        ]
    )
    result = loan_type.build_loan_type_variant_graph_document_v1([page])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["graphs"] == []
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "INSUFFICIENT_DISTINCT_LOAN_TYPE_ROLES"
    ]


def test_two_full_tables_in_one_document_fail_uniqueness() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(_direct(), page_sequence=1), _page(_direct(), page_sequence=2)]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"] == {
        "full_match_count": 2,
        "status": "AMBIGUOUS_MULTIPLE_FULL_MATCHES",
    }


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_direct())]
    result = loan_type.build_loan_type_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ltvgv1:result:" + loan_type.canonical_json_sha256_v1(material)

    with pytest.raises(loan_type.LoanTypeVariantGraphV1Error, match="replay exactly"):
        loan_type.validate_loan_type_variant_graph_replay_v1(forged, pages)


def test_extended_compact_sibling_boundary_prevents_duplicate_later_margin_row() -> None:
    surfaces = _direct()[:-3]
    surfaces.extend(
        [
            ("120", 500, 345),
            ("106", 800, 345),
            ("Theo đối tượng khách hàng", 0, 390),
            ("Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán", 0, 435),
            ("5", 500, 435),
            ("4", 800, 435),
        ]
    )

    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_owner_table_variants=True
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert [row["role"] for row in result["graphs"][0]["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "DISCOUNT_INSTRUMENTS",
        "FINANCIAL_LEASE",
        "PAYMENTS_ON_BEHALF",
        "ENTRUSTED_OR_SPONSORED_CAPITAL",
    ]


def test_extended_quality_sibling_heading_ends_the_implicit_type_table() -> None:
    surfaces = _direct()[:-3]
    surfaces.extend(
        [
            ("120", 500, 345),
            ("106", 800, 345),
            ("Phân tích dư nợ theo chất lượng nợ cho vay như sau", 0, 390),
            ("Nợ đủ tiêu chuẩn", 0, 435),
            ("110", 500, 435),
            ("96", 800, 435),
            ("Nợ cần chú ý", 0, 480),
            ("10", 500, 480),
            ("10", 800, 480),
            ("120", 500, 525),
            ("106", 800, 525),
        ]
    )

    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_owner_table_variants=True
    )

    graph = result["graphs"][0]
    assert graph["intermediate_totals"] == []
    assert [item["semantic_surface"] for item in graph["total"]] == ["120", "106"]


def test_extended_year_end_axis_and_source_semantic_aliases_are_generic() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Số cuối năm", 500, 40),
        ("Số đầu năm", 800, 40),
        ("Triệu VND", 500, 70),
        ("Triệu VND", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Các khoản phải thu từ cho thuê tài chính", 0, 165),
        ("5", 500, 165),
        ("4", 800, 165),
        (
            "Cho vay trong nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản trả ngay",
            0,
            210,
        ),
        ("2", 500, 210),
        ("1", 800, 210),
        ("107", 500, 255),
        ("95", 800, 255),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_owner_table_variants=True
    )

    graph = result["graphs"][0]
    assert graph["period_mode"] == "LOCAL_RELATIVE_YEAR_END_PERIOD_ROLES"
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "FINANCIAL_LEASE",
        "OTHER_LOANS",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_standalone_footnote_after_totals_is_not_joined_to_wrapped_last_label() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Số cuối năm", 500, 40),
        ("Số đầu năm", 800, 40),
        ("Triệu VND", 500, 70),
        ("Triệu VND", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Nghiệp vụ phát hành thư tín dụng trả chậm", 0, 165),
        ("phát sinh trước ngày 01 tháng 7 năm 2024", 0, 195),
        ("1", 800, 195),
        ("100", 500, 240),
        ("91", 800, 240),
        ("(i)", 0, 300),
    ]
    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_owner_table_variants=True
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["rows"][-1]["label"]["source_line_indices"] == [8, 9]
    assert [item["semantic_surface"] for item in graph["total"]] == ["100", "91"]
