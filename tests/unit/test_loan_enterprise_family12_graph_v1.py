from __future__ import annotations

import copy

import pytest

import bctc_ai.evaluation.accounting_semantic_region_graph_v1 as semantic_region_module
import bctc_ai.evaluation.loan_enterprise_family12_graph_v1 as family12_graph_module
from bctc_ai.evaluation.accounting_scoped_table_graph_v1 import (
    AccountingScopedTableGraphV1Error,
)
from bctc_ai.evaluation.loan_enterprise_family12_graph_v1 import (
    LoanEnterpriseFamily12GraphV1Error,
    build_loan_enterprise_family12_graph_v1,
    validate_loan_enterprise_family12_graph_replay_v1,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    build_loan_enterprise_family12_spec_v1,
)


def _line(index: int, text: str, x1: int, y1: int, x2: int, y2: int) -> dict:
    return {
        "bbox": [x1, y1, x2, y2],
        "source_line_index": index,
        "source_text": text,
        "vietocr_text": text,
    }


def _page(sequence: int, lines: list[dict]) -> dict:
    return {
        "lines": lines,
        "page_height": 1_500,
        "page_sequence": sequence,
        "page_width": 1_000,
    }


def _table_lines(
    *,
    owner: str = "Cho vay khách hàng",
    heading: str = "Phân tích theo loại hình doanh nghiệp",
    rows: list[str] | None = None,
) -> list[dict]:
    rows = rows or ["Công ty TNHH", "Công ty cổ phần khác"]
    lines = [
        _line(0, owner, 40, 40, 410, 70),
        _line(1, heading, 40, 110, 760, 140),
    ]
    for ordinal, row in enumerate(rows):
        y = 200 + ordinal * 50
        lines.extend(
            [
                _line(2 + ordinal * 2, row, 70, y, 570, y + 28),
                _line(3 + ordinal * 2, str((ordinal + 1) * 100), 730, y, 820, y + 28),
            ]
        )
    return lines


def _binding_ids(result: dict) -> list[int]:
    return [
        binding["report_norm_id"]
        for region in result["regions"]
        for binding in region["binding_proposals"]
    ]


def _row_by_surface(result: dict, surface: str) -> dict:
    return next(
        row
        for region in result["regions"]
        for row in region["row_proposals"]
        if row["surface"] == surface
    )


def test_spec_locks_schema_history_and_safety_policy() -> None:
    spec = build_loan_enterprise_family12_spec_v1()

    assert spec["report_norm_id"] == 766
    assert spec["parent_report_norm_id"] == 716
    assert [child["report_norm_id"] for child in spec["children"]] == [
        767,
        768,
        769,
        770,
        771,
        772,
        773,
        774,
        775,
        776,
        6074,
        777,
        778,
        779,
        780,
        781,
        782,
        6058,
        5748,
    ]
    assert spec["historical_evidence_summary"] == {
        "bounded_absence_filing_count": 56,
        "exact_child_absence_report_norm_ids": [775, 777],
        "owner_carried_at_most_two_pages_present_count": 20,
        "present_filing_count": 84,
        "same_page_owner_present_count": 64,
        "studied_filing_count": 140,
    }
    assert spec["safety"]["foreign_branch_or_subsidiary_allowed_report_norm_ids"] == [6058]
    assert spec["safety"]["foreign_branch_or_subsidiary_forbidden_report_norm_ids"] == [
        765,
        782,
    ]
    schema_parents = {
        child["report_norm_id"]: child["schema_parent_report_norm_id"] for child in spec["children"]
    }
    assert schema_parents[6058] == 727
    assert {parent for child, parent in schema_parents.items() if child != 6058} == {766}
    assert spec["safety"]["mapping_authority"] is False
    assert [item["component_id"] for item in spec["branch_components"]] == [
        "BRANCH_LOAI_HINH_DOANH_NGHIEP",
        "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
    ]
    deposit_1075 = next(
        item for item in spec["context_classes"] if item["context_id"] == "DEPOSIT_1075"
    )
    owner_716 = next(item for item in spec["context_classes"] if item["context_id"] == "OWNER_716")
    assert "Theo loại hình doanh nghiệp" not in deposit_1075["aliases"]
    assert "Loại hình doanh nghiệp" not in deposit_1075["aliases"]
    assert owner_716.get("allow_token_subsequence_fence", False) is False
    assert all(
        item.get("allow_token_subsequence_fence") is True
        for item in spec["context_classes"]
        if item["disposition"] == "HARD_VETO"
    )


@pytest.mark.parametrize(
    "heading",
    [
        "Theo loại hình doanh nghiệp",
        "Loại hình doanh nghiệp",
        "Phân tích dư nợ cho vay khách hàng theo loại hình doanh nghiệp",
        (
            "Phân tích dư nợ cho vay khách hàng theo đối tượng khách hàng "
            "và theo loại hình doanh nghiệp"
        ),
    ],
)
def test_generic_and_vpb_inserted_word_headings_need_and_accept_owner716(heading: str) -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines(heading=heading))])

    assert len(result["regions"]) == 1
    assert _binding_ids(result) == [768, 773]
    assert result["regions"][0]["owner_context"]["report_norm_id"] == 716
    assert result["regions"][0]["shared_scoped_table_v1"]["enforcement"] == ("ADVISORY_CHALLENGER")
    resolution = result["regions"][0]["minimal_unique_anchor_resolution_v1"]
    assert resolution["selected_anchor_ids"] == ["PARENT_RNID_766", "CHILD_RNID_768"]
    assert resolution["selected_size"] == 2
    assert resolution["matching_count"] == 1
    assert result["safety"]["minimal_unique_pair_or_triple_required_for_complete_region"] is True
    assert result["safety"]["parent_child_anchor_pairs_precede_child_child_pairs"] is True
    assert (
        "minimal_unique_parent_child_or_triple_required_for_complete_region" not in result["safety"]
    )


@pytest.mark.parametrize(
    ("heading", "tier", "basis", "component_ids"),
    [
        (
            "Phân tích dư nợ cho vay theo đối turọng khách hàng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTED_ALIAS",
            "DECLARATIVE_BRANCH_COMPONENT",
            ["BRANCH_LOAI_HINH_DOANH_NGHIEP"],
        ),
        (
            "Phân tích dư nợ cho vay theo đối trọng khách hàng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTED_ALIAS",
            "DECLARATIVE_BRANCH_COMPONENT",
            ["BRANCH_LOAI_HINH_DOANH_NGHIEP"],
        ),
        (
            "Phân tích dư nợ cho vay theo đổi tượng khách hàng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTLESS_ALIAS",
            "FULL_BRANCH_ALIAS",
            [],
        ),
        (
            "Phân tích dư nợ cho vay theo đối tượng khách hằng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTLESS_ALIAS",
            "FULL_BRANCH_ALIAS",
            [],
        ),
    ],
)
def test_branch_ocr_variants_use_exact_then_one_edit_only_on_miss(
    heading: str,
    tier: str,
    basis: str,
    component_ids: list[str],
) -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines(heading=heading))])

    branch = result["regions"][0]["branch"]
    assert branch["match_tier"] == tier
    assert branch["match_basis"] == basis
    assert branch["matched_component_ids"] == component_ids
    assert _binding_ids(result) == [768, 773]


@pytest.mark.parametrize(
    ("heading", "tier", "component_id"),
    [
        (
            "Dư nợ cho vay được trình bày theo đối tượng khách hàng",
            "EXACT_ACCENTED_ALIAS",
            "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
        ),
        (
            "Theo đối tượng khách hàng",
            "EXACT_ACCENTED_ALIAS",
            "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
        ),
        (
            "Dư nợ phân theo loại hình doanh nghiệp như sau:",
            "EXACT_ACCENTED_ALIAS",
            "BRANCH_LOAI_HINH_DOANH_NGHIEP",
        ),
        (
            "Cho vay khách hàng, chi tiết theo loại hình doanh nghiệp",
            "EXACT_ACCENTED_ALIAS",
            "BRANCH_LOAI_HINH_DOANH_NGHIEP",
        ),
        (
            "Dư nợ theo đối turọng khách hàng",
            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
            "BRANCH_THEO_DOI_TUONG_KHACH_HANG",
        ),
    ],
)
def test_component_fallback_covers_historical_heading_classes(
    heading: str, tier: str, component_id: str
) -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines(heading=heading))])

    branch = result["regions"][0]["branch"]
    assert branch["match_basis"] == "DECLARATIVE_BRANCH_COMPONENT"
    assert branch["match_tier"] == tier
    assert component_id in branch["matched_component_ids"]
    assert _binding_ids(result) == [768, 773]


def test_split_heading_and_tightly_wrapped_child_label_are_composed() -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, "Phân tích dư nợ cho vay theo đối tượng khách hàng", 40, 105, 760, 130),
        _line(2, "và theo loại hình doanh nghiệp", 40, 134, 600, 159),
        _line(3, "Dịch vụ hành chính sự nghiệp, Đảng,", 70, 200, 560, 222),
        _line(4, "đoàn thể, hiệp hội", 70, 226, 420, 248),
        _line(5, "100", 730, 226, 820, 248),
        _line(6, "Công ty TNHH", 70, 280, 420, 302),
        _line(7, "200", 730, 280, 820, 302),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert _binding_ids(result) == [768, 781]
    assert result["regions"][0]["branch"]["surface"] == (
        "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp"
    )


def test_split_component_fallback_is_geometry_cohesive_and_provider_order_invariant() -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, "Dư nợ trình bày theo đối tượng", 40, 105, 700, 130),
        _line(2, "khách hàng, như sau:", 40, 134, 430, 159),
        _line(3, "Công ty TNHH", 70, 210, 500, 238),
        _line(4, "100", 730, 210, 820, 238),
        _line(5, "Công ty cổ phần khác", 70, 260, 570, 288),
        _line(6, "200", 730, 260, 820, 288),
    ]
    expected = build_loan_enterprise_family12_graph_v1([_page(1, lines)])
    reordered = copy.deepcopy(lines)
    reordered.reverse()

    assert expected["regions"][0]["branch"]["match_basis"] == ("DECLARATIVE_BRANCH_COMPONENT")
    assert len(expected["regions"][0]["branch"]["evidence"]) == 2
    assert build_loan_enterprise_family12_graph_v1([_page(1, reordered)]) == expected


def test_distinct_exact_and_fuzzy_regions_with_same_topology_both_fail_closed() -> None:
    lines = [
        *_table_lines(rows=["Công ty TNHH"]),
        _line(20, "Cho vay khách hàng", 40, 380, 410, 410),
        _line(21, "Chi tiết loại hình doanh nghiệx", 40, 450, 650, 480),
        _line(22, "Công ty TNHH", 70, 540, 500, 568),
        _line(23, "300", 730, 540, 820, 568),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["metrics"]["branch_candidate_count"] == 2
    assert result["metrics"]["minimal_anchor_collision_demoted_region_count"] == 2
    assert {near["branch"]["match_tier"] for near in result["near_regions"]} == {
        "EXACT_ACCENTED_ALIAS",
        "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
    }
    assert {
        near["minimal_unique_anchor_resolution_v1"]["status"] for near in result["near_regions"]
    } == {"UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE_COMBINATION"}


def test_distinct_regions_with_unique_parent_child_pairs_are_both_retained() -> None:
    lines = [
        *_table_lines(rows=["Công ty TNHH"]),
        _line(20, "Cho vay khách hàng", 40, 380, 410, 410),
        _line(21, "Chi tiết loại hình doanh nghiệp", 40, 450, 650, 480),
        _line(22, "Doanh nghiệp nhà nước", 70, 540, 500, 568),
        _line(23, "300", 730, 540, 820, 568),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert len(result["regions"]) == 2
    assert result["metrics"]["minimal_anchor_collision_demoted_region_count"] == 0
    assert {
        tuple(region["minimal_unique_anchor_resolution_v1"]["selected_anchor_ids"])
        for region in result["regions"]
    } == {
        ("PARENT_RNID_766", "CHILD_RNID_767"),
        ("PARENT_RNID_766", "CHILD_RNID_768"),
    }


def test_hard_veto_near_region_controls_topology_but_never_promotes() -> None:
    lines = [
        *_table_lines(rows=["Công ty TNHH"]),
        _line(20, "Tiền gửi của khách hàng", 40, 380, 500, 410),
        _line(21, "Loại hình doanh nghiệp", 40, 450, 650, 480),
        _line(22, "Công ty TNHH", 70, 540, 500, 568),
        _line(23, "300", 730, 540, 820, 568),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert _binding_ids(result) == [768]
    assert result["metrics"]["minimal_anchor_topology_candidate_count"] == 2
    assert result["metrics"]["minimal_anchor_collision_demoted_region_count"] == 0
    assert len(result["near_regions"]) == 1
    veto = result["near_regions"][0]
    assert veto["reason"] == "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET"
    assert veto["source_only_binding_proposals"] == []
    assert veto["source_only_row_proposals"][0]["report_norm_id"] == 768
    candidates = result["minimal_unique_anchor_resolution_v1"]["candidates"]
    veto_candidate = next(item for item in candidates if item["disposition"] == "NEAR")
    assert veto_candidate["parent_anchor_id"] is None
    assert result["regions"][0]["minimal_unique_anchor_resolution_v1"]["selected_anchor_ids"] == [
        "PARENT_RNID_766",
        "CHILD_RNID_768",
    ]


def test_owner_accepted_duplicate_near_region_collides_with_complete_parent_child_pair() -> None:
    lines = [
        *_table_lines(rows=["Công ty TNHH"]),
        _line(20, "Cho vay khách hàng", 40, 380, 410, 410),
        _line(21, "Chi tiết loại hình doanh nghiệp", 40, 450, 650, 480),
        _line(22, "Công ty TNHH", 70, 540, 500, 568),
        _line(23, "300", 730, 540, 820, 568),
        _line(24, "Công ty TNHH", 70, 590, 500, 618),
        _line(25, "400", 730, 590, 820, 618),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["metrics"]["minimal_anchor_collision_demoted_region_count"] == 1
    candidates = result["minimal_unique_anchor_resolution_v1"]["candidates"]
    owner_accepted_near = next(item for item in candidates if item["disposition"] == "NEAR")
    assert owner_accepted_near["parent_anchor_id"] == "PARENT_RNID_766"
    assert owner_accepted_near["child_anchor_ids"] == ["CHILD_RNID_768"]
    assert {
        near["minimal_unique_anchor_resolution_v1"]["status"] for near in result["near_regions"]
    } == {"UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE_COMBINATION"}


def test_hdb_owner_context_can_carry_exactly_two_pages() -> None:
    pages = [
        _page(20, [_line(0, "Cho vay khách hàng", 40, 80, 410, 110)]),
        _page(21, [_line(0, "Đơn vị: triệu đồng", 600, 80, 900, 110)]),
        _page(
            22,
            _table_lines()[1:],
        ),
    ]

    result = build_loan_enterprise_family12_graph_v1(pages)

    assert len(result["regions"]) == 1
    owner = result["regions"][0]["owner_context"]
    assert owner["mode"] == "CARRIED_FROM_PREVIOUS_PAGE_2"
    assert owner["page_distance"] == 2
    assert result["regions"][0]["shared_scoped_table_v1"]["status"] == (
        "NOT_APPLICABLE_TO_EXPLICIT_CROSS_PAGE_OWNER_CARRY_RECEIPT"
    )


def test_owner_beyond_two_pages_is_not_inferred() -> None:
    pages = [
        _page(20, [_line(0, "Cho vay khách hàng", 40, 80, 410, 110)]),
        _page(21, [_line(0, "Đơn vị: triệu đồng", 600, 80, 900, 110)]),
        _page(22, [_line(0, "Đơn vị: triệu đồng", 600, 80, 900, 110)]),
        _page(23, _table_lines()[1:]),
    ]

    result = build_loan_enterprise_family12_graph_v1(pages)

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES"
    )


def test_owner_carry_fails_closed_when_intervening_page_is_not_supplied() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(20, [_line(0, "Cho vay khách hàng", 40, 80, 410, 110)]),
            _page(22, _table_lines()[1:]),
        ]
    )

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == ("OWNER_CARRY_HAS_UNOBSERVED_INTERVENING_PAGE")


def test_mbb_specific_state_rows_win_and_unqualified_tnhh_maps_768() -> None:
    rows = [
        "Công ty TNHH",
        "Công ty TNHH MTV do Nhà nước sở hữu 100% vốn điều lệ",
        "Công ty cổ phần có trên 50% vốn điều lệ do Nhà nước sở hữu",
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines(rows=rows))])

    assert _binding_ids(result) == [768, 769, 772]
    assert _row_by_surface(result, "Công ty TNHH")["match_tier"] == "EXACT_ACCENTED_ALIAS"


def test_accentless_vietnamese_row_maps_without_fuzzy_authority() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Cong ty TNHH", "Cong ty co phan khac"]))]
    )

    assert _binding_ids(result) == [768, 773]
    assert all(
        row["match_tier"] == "EXACT_ACCENTLESS_ALIAS"
        for row in result["regions"][0]["row_proposals"]
    )


def test_unqualified_and_acb_combined_rows_remain_source_only_ambiguous() -> None:
    ambiguous = [
        "Công ty cổ phần",
        "Hợp tác xã",
        "Cá nhân",
        "Công ty cổ phần, công ty TNHH và doanh nghiệp khác",
    ]
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Công ty TNHH", *ambiguous]))]
    )

    assert _binding_ids(result) == [768]
    for surface in ambiguous:
        row = _row_by_surface(result, surface)
        assert row["report_norm_id"] is None
        assert row["status"] == "SOURCE_ONLY_AMBIGUOUS"
    assert _row_by_surface(result, ambiguous[-1])["candidate_report_norm_ids"] == [
        768,
        773,
        774,
        775,
    ]


def test_source_only_rows_are_retained_when_no_schema_binding_survives() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Công ty cổ phần", "Hợp tác xã"]))]
    )

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == ("NO_UNIQUE_SCHEMA_ROW_WITH_VALUE_GEOMETRY")
    rows = result["near_regions"][0]["source_only_row_proposals"]
    assert [row["status"] for row in rows] == [
        "SOURCE_ONLY_AMBIGUOUS",
        "SOURCE_ONLY_AMBIGUOUS",
    ]
    assert result["near_regions"][0]["source_only_geometry_proposal"] is not None
    assert result["near_regions"][0]["shared_scoped_table_v1"]["enforcement"] == (
        "ADVISORY_CHALLENGER"
    )
    assert result["near_regions"][0]["shared_scoped_table_v1"]["status"] == (
        "NOT_RUN_INSUFFICIENT_ROLE_TOPOLOGY"
    )


def test_numeric_cell_between_labels_prevents_false_wrapped_label_composition() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Công ty TNHH", "Khác"]))]
    )

    assert _binding_ids(result) == [768, 782]
    assert _row_by_surface(result, "Công ty TNHH")["report_norm_id"] == 768
    assert _row_by_surface(result, "Khác")["report_norm_id"] == 782


@pytest.mark.parametrize(
    "poison",
    [
        "Tiền gửi của khách hàng",
        "Phân tích tiền gửi khách hàng theo loại hình doanh nghiệp",
        "IV. Một số thông tin khác",
        "Giao dịch với các bên liên quan",
        "Giao dịch tiền gửi tại MB",
    ],
)
def test_deposit_and_related_party_closest_contexts_are_hard_veto(poison: str) -> None:
    lines = _table_lines()
    lines[0] = _line(0, poison, 40, 40, 650, 70)

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET"
    )


def test_deposit_owner_with_generic_component_heading_remains_hard_veto() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(
                1,
                _table_lines(
                    owner="Tiền gửi của khách hàng",
                    heading="Loại hình doanh nghiệp",
                ),
            )
        ]
    )

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET"
    )
    assert (
        result["near_regions"][0]["owner_context"]["closest_context_event"]["context_id"]
        == "DEPOSIT_1055"
    )


@pytest.mark.parametrize(
    ("poison", "context_id"),
    [
        ("Tiền gửi củ khách hàng", "DEPOSIT_1055"),
        ("Tiền gởi của khách hàng", "DEPOSIT_1055"),
        ("Tiền gửi của khách hàn", "DEPOSIT_1055"),
        ("Tài sả cố định", "STRUCTURAL_RESET"),
    ],
)
def test_one_edit_context_fence_cannot_be_absorbed_into_component_branch(
    poison: str, context_id: str
) -> None:
    lines = _table_lines(heading="Loại hình doanh nghiệp")
    lines.insert(1, _line(20, poison, 40, 80, 620, 105))

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert len(result["near_regions"]) == 1
    near = result["near_regions"][0]
    assert near["branch"]["surface"] == "Loại hình doanh nghiệp"
    assert near["reason"] == "CLOSEST_CONTEXT_IS_HARD_VETO_OR_STRUCTURAL_RESET"
    assert near["owner_context"]["closest_context_event"]["context_id"] == context_id


@pytest.mark.parametrize("deposit_first", ["Tiền gửi của", "Tiền gửi củ"])
def test_wrapped_deposit_context_event_vetoes_following_generic_branch(
    deposit_first: str,
) -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, deposit_first, 40, 90, 420, 112),
        _line(2, "khách hàng", 40, 116, 300, 138),
        _line(3, "Loại hình doanh nghiệp", 40, 190, 650, 218),
        _line(4, "Công ty TNHH", 70, 260, 500, 288),
        _line(5, "100", 730, 260, 820, 288),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert len(result["near_regions"]) == 1
    closest = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert closest["disposition"] == "HARD_VETO"
    assert len(closest["evidence"]) == 2
    assert result["metrics"]["context_event_wrapped_count"] == 1


def test_wrapped_deposit_event_fences_the_component_line_inside_its_interval() -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, "Phân tích tiền gửi khách hàng theo", 40, 90, 650, 112),
        _line(2, "loại hình doanh nghiệp", 40, 116, 500, 138),
        _line(3, "Công ty TNHH", 70, 200, 500, 228),
        _line(4, "100", 730, 200, 820, 228),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["near_regions"] == []
    assert result["metrics"]["branch_candidate_count"] == 0
    assert result["metrics"]["context_event_wrapped_count"] == 1


@pytest.mark.parametrize(
    ("poison", "context_id"),
    [
        (
            "Phân tích tiền gửi khách hàng theo loại hình doanh nghiệp và các chi tiết",
            "DEPOSIT_1075",
        ),
        (
            "Phân tích theo ngành nghề kinh doanh và loại hình doanh nghiệp",
            "STRUCTURAL_RESET",
        ),
        (
            "Phân tíc tiền gửi khách hàng theo loại hình doanh nghiệp và các chi tiết",
            "DEPOSIT_1055",
        ),
        (
            "Phân tíc theo ngành nghề kinh doanh và loại hình doanh nghiệp",
            "STRUCTURAL_RESET",
        ),
    ],
)
def test_long_hard_veto_or_reset_component_precedes_branch_substring(
    poison: str, context_id: str
) -> None:
    lines = _table_lines(heading="Loại hình doanh nghiệp")
    lines.insert(1, _line(20, poison, 40, 80, 900, 105))

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert len(result["near_regions"]) == 1
    event = result["near_regions"][0]["owner_context"]["closest_context_event"]
    assert event["context_id"] == context_id
    assert event["disposition"] == "HARD_VETO"


@pytest.mark.parametrize(
    "poison_branch",
    [
        "Các giao dịch với bên liên quan theo loại hình doanh nghiệp",
        "Các giao dịch với bên liên quax theo loại hình doanh nghiệp",
        "Giao dịch tiền gửi với MB theo loại hình doanh nghiệp",
        "Giao dịch tiền gửi với MX theo loại hình doanh nghiệp",
    ],
)
def test_related_party_exact_and_one_edit_suffix_cannot_become_family_branch(
    poison_branch: str,
) -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, poison_branch, 40, 110, 900, 140),
        _line(2, "Công ty TNHH", 70, 200, 570, 228),
        _line(3, "100", 730, 200, 820, 228),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["near_regions"] == []
    assert result["metrics"]["branch_candidate_count"] == 0


def test_branch_containing_loan_owner_words_does_not_gain_hard_veto_containment() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(
                1,
                _table_lines(heading="Phân tích cho vay khách hàng theo loại hình doanh nghiệp"),
            )
        ]
    )

    assert _binding_ids(result) == [768, 773]
    assert result["regions"][0]["owner_context"]["report_norm_id"] == 716


def test_closer_reset_poison_overrides_previous_owner() -> None:
    lines = _table_lines()
    lines.insert(1, _line(20, "Chứng khoán đầu tư", 40, 80, 410, 105))

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert (
        result["near_regions"][0]["owner_context"]["closest_context_event"]["context_id"]
        == "STRUCTURAL_RESET"
    )


def test_next_table_poison_closes_body_before_role_looking_rows() -> None:
    lines = _table_lines(rows=["Công ty TNHH", "Công ty cổ phần khác"])
    lines.extend(
        [
            _line(20, "Giao dịch với các bên liên quan", 40, 350, 600, 378),
            _line(21, "Doanh nghiệp nhà nước", 70, 400, 500, 428),
            _line(22, "900", 730, 400, 820, 428),
        ]
    )

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert _binding_ids(result) == [768, 773]
    assert all(binding != 767 for binding in _binding_ids(result))


def test_heading_alone_never_becomes_owner() -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines()[1:])])

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES"
    )


@pytest.mark.parametrize(
    "lines",
    [
        [_line(0, "Loại hình doanh nghiệp", 40, 110, 600, 140)],
        [
            _line(0, "Loại hình doanh nghiệp", 40, 110, 600, 140),
            _line(1, "Nội dung không thuộc schema", 70, 200, 550, 228),
            _line(2, "100", 730, 200, 820, 228),
        ],
        [
            _line(0, "Tiền gửi của khách hàng", 40, 40, 500, 70),
            _line(1, "Loại hình doanh nghiệp", 40, 110, 600, 140),
            _line(2, "Nội dung không thuộc schema", 70, 200, 550, 228),
            _line(3, "100", 730, 200, 820, 228),
        ],
    ],
)
def test_anchorless_near_region_is_retained_without_entering_topology_resolver(
    lines: list[dict],
) -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert len(result["near_regions"]) == 1
    near = result["near_regions"][0]
    assert near["topology_candidate_id"] is None
    assert near["minimal_unique_anchor_resolution_v1"]["status"] == (
        "NOT_RUN_ANCHORLESS_NEAR_CANDIDATE"
    )
    assert result["minimal_unique_anchor_resolution_v1"] is None
    assert result["metrics"]["minimal_anchor_topology_candidate_count"] == 0
    assert result["metrics"]["minimal_anchor_anchorless_near_region_count"] == 1


def test_owner_and_component_without_child_value_geometry_cannot_bind() -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, "Loại hình doanh nghiệp", 40, 110, 600, 140),
        _line(2, "Nội dung không phải khoản mục", 70, 200, 550, 228),
        _line(3, "100", 730, 200, 820, 228),
    ]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == ("NO_UNIQUE_SCHEMA_ROW_WITH_VALUE_GEOMETRY")
    assert result["safety"]["single_branch_component_can_create_binding_proposal"] is False
    assert (
        result["safety"]["owner_branch_and_child_value_geometry_required_for_binding_proposal"]
        is True
    )


def test_two_role_investment_pair_fails_without_loan_owner() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(
                1,
                _table_lines(
                    owner="Các khoản đầu tư dài hạn khác",
                    heading="Theo loại hình doanh nghiệp",
                    rows=["Công ty liên doanh, hợp doanh", "Công ty hợp danh"],
                ),
            )
        ]
    )

    assert result["regions"] == []
    assert result["safety"]["two_role_table_without_owner_716_can_accept"] is False


def test_subsidiary_context_cannot_replace_explicit_loan_owner() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(
                1,
                _table_lines(
                    owner="Chi nhánh và công ty con tại nước ngoài",
                    heading="Dư nợ theo đối tượng khách hàng",
                ),
            )
        ]
    )

    assert result["regions"] == []
    assert result["near_regions"][0]["reason"] == (
        "EXPLICIT_OWNER_716_NOT_FOUND_WITHIN_TWO_PRECEDING_PAGES"
    )


def test_foreign_branch_component_binds_exact_6058_while_other_remains_782() -> None:
    foreign = "Cho vay tại chi nhánh và ngân hàng con nước ngoài"
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Khác", foreign]))]
    )

    assert _binding_ids(result) == [782, 6058]
    assert 765 not in _binding_ids(result)
    binding = next(
        item for item in result["regions"][0]["binding_proposals"] if item["report_norm_id"] == 6058
    )
    assert binding["foreign_branch_or_subsidiary_component"] is True
    assert _row_by_surface(result, foreign)["report_norm_id"] == 6058
    assert _row_by_surface(result, foreign)["binding_class"] == (
        "EXACT_FOREIGN_BRANCH_OR_SUBSIDIARY_INDUSTRY_LEAF"
    )
    assert _row_by_surface(result, "Khác")["report_norm_id"] == 782


def test_775_and_777_are_exact_only_not_recovered_from_typo() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [
            _page(
                1,
                _table_lines(
                    rows=[
                        "Công ty TNHH",
                        "Công ty CP, TNHH, DN tư nhân",
                        "Công ty liên doan, hợp doanh",
                    ]
                ),
            )
        ]
    )

    assert _binding_ids(result) == [768, 775]
    assert all(
        row["candidate_report_norm_ids"] != [777] for row in result["regions"][0]["row_proposals"]
    )


def test_label_without_visible_value_geometry_cannot_bind() -> None:
    lines = _table_lines(rows=["Công ty TNHH", "Công ty cổ phần khác"])
    lines = [line for line in lines if line["vietocr_text"] != "200"]

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert _binding_ids(result) == [768]
    row = _row_by_surface(result, "Công ty cổ phần khác")
    assert row["status"] == "TEXT_ROLE_PROPOSAL_MISSING_ROW_VALUE_GEOMETRY"


def test_provider_and_page_reordering_does_not_change_result() -> None:
    first = _page(7, [_line(0, "Cho vay khách hàng", 40, 80, 410, 110)])
    second = _page(
        8,
        _table_lines(heading="Dư nợ phân theo loại hình doanh nghiệp như sau")[1:],
    )
    canonical = build_loan_enterprise_family12_graph_v1([first, second])
    reordered = copy.deepcopy([second, first])
    for page in reordered:
        page["lines"].reverse()

    assert build_loan_enterprise_family12_graph_v1(reordered) == canonical


def test_exact_replay_accepts_original_and_rejects_tamper() -> None:
    pages = [_page(1, _table_lines())]
    result = build_loan_enterprise_family12_graph_v1(pages)

    assert validate_loan_enterprise_family12_graph_replay_v1(result, pages) == result
    tampered = copy.deepcopy(result)
    tampered["metrics"]["region_count"] = 0
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="content identity drifted"):
        validate_loan_enterprise_family12_graph_replay_v1(tampered, pages)


def test_historical_84_56_metadata_never_changes_matching_or_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = [_page(1, _table_lines())]
    baseline = build_loan_enterprise_family12_graph_v1(pages)
    altered_spec = build_loan_enterprise_family12_spec_v1()
    altered_spec["historical_evidence_summary"] = {
        "bounded_absence_filing_count": 140,
        "exact_child_absence_report_norm_ids": [],
        "owner_carried_at_most_two_pages_present_count": 0,
        "present_filing_count": 0,
        "same_page_owner_present_count": 0,
        "studied_filing_count": 140,
    }
    monkeypatch.setattr(
        family12_graph_module,
        "build_loan_enterprise_family12_spec_v1",
        lambda: copy.deepcopy(altered_spec),
    )

    changed = build_loan_enterprise_family12_graph_v1(pages)

    assert changed["regions"] == baseline["regions"]
    assert changed["metrics"] == baseline["metrics"]
    assert changed["safety"]["historical_evidence_metadata_used_for_matching"] is False
    assert changed["historical_evidence_summary"] != baseline["historical_evidence_summary"]


def test_shared_scoped_failure_is_an_advisory_challenge_with_exact_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject(*_args: object, **_kwargs: object) -> dict:
        raise AccountingScopedTableGraphV1Error("synthetic scoped failure")

    monkeypatch.setattr(
        semantic_region_module,
        "build_accounting_scoped_table_graph_v1",
        _reject,
    )

    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines())])

    assert _binding_ids(result) == [768, 773]
    shared = result["regions"][0]["shared_scoped_table_v1"]
    assert shared == {
        "enforcement": "ADVISORY_CHALLENGER",
        "reason": "SCOPED_TABLE_V1_REJECTED_DYNAMIC_EXACT_SPEC",
        "result": None,
        "status": "SHARED_SCOPED_TABLE_FAIL_CLOSED",
    }
    assert result["metrics"]["scoped_table_advisory_failure_region_count"] == 1
    assert result["metrics"]["unique_binding_proposal_count"] == 2
    assert result["safety"]["shared_semantic_region_failure_can_promote_mapping"] is False


def test_no_branch_is_only_bounded_absence() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, [_line(0, "Cho vay khách hàng", 40, 80, 410, 110)])]
    )

    assert result["regions"] == []
    assert result["near_regions"] == []
    assert result["bounded_absences"][0]["status"] == ("BOUNDED_ABSENCE_NO_GLOBAL_CORPUS_CLAIM")


def test_input_contract_rejects_duplicate_source_indices() -> None:
    lines = _table_lines()
    lines[1]["source_line_index"] = lines[0]["source_line_index"]

    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="source line index repeats"):
        build_loan_enterprise_family12_graph_v1([_page(1, lines)])


def _branchless_owner_two_child_lines() -> list[dict]:
    return [
        _line(0, "Cho vay khách hàng", 40, 40, 410, 70),
        _line(1, "Công ty TNHH", 70, 130, 570, 158),
        _line(2, "100", 730, 130, 820, 158),
        _line(3, "Công ty cổ phần khác", 70, 190, 570, 218),
        _line(4, "200", 730, 190, 820, 218),
    ]


def test_semantic_near_is_unresolved_and_never_bounded_absence() -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines()[1:])])

    assert result["regions"] == []
    assert result["near_regions"][0]["disposition"] == "UNRESOLVED"
    assert result["bounded_absences"] == []
    assert result["metrics"]["bounded_absence_count"] == 0
    assert result["metrics"]["unresolved_region_count"] == 1


def test_branchless_owner_and_two_distinct_children_veto_bounded_absence() -> None:
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _branchless_owner_two_child_lines())]
    )

    assert result["regions"] == []
    assert result["near_regions"] == []
    assert result["bounded_absences"] == []
    assert result["metrics"]["branchless_rescue_challenger_count"] == 1
    challenger = result["branchless_rescue_challengers"][0]
    assert challenger["disposition"] == "UNRESOLVED"
    assert challenger["candidate_child_report_norm_ids"] == [768, 773]
    assert (
        challenger["source_page_evidence_sha256"]
        == result["evidence_binding"]["canonical_page_evidence_sha256"]
    )


def test_branchless_rescue_rejects_reset_between_and_cross_page_borrowing() -> None:
    reset_between = _branchless_owner_two_child_lines()
    reset_between.insert(1, _line(9, "Tài sản cố định", 40, 90, 410, 118))
    result = build_loan_enterprise_family12_graph_v1([_page(1, reset_between)])

    assert result["branchless_rescue_challengers"] == []
    assert result["metrics"]["bounded_absence_count"] == 1

    cross_page = build_loan_enterprise_family12_graph_v1(
        [
            _page(1, [_branchless_owner_two_child_lines()[0]]),
            _page(2, _branchless_owner_two_child_lines()[1:]),
        ]
    )
    assert cross_page["branchless_rescue_challengers"] == []
    assert cross_page["metrics"]["bounded_absence_count"] == 1


def test_branchless_rescue_before_following_reset_is_retained() -> None:
    lines = _branchless_owner_two_child_lines()
    lines.append(_line(9, "Tài sản cố định", 40, 270, 410, 298))

    result = build_loan_enterprise_family12_graph_v1([_page(1, lines)])

    assert result["bounded_absences"] == []
    challenger = result["branchless_rescue_challengers"][0]
    assert challenger["reset_fence"]["preceding_context_event_id"] is None
    assert type(challenger["reset_fence"]["following_context_event_id"]) is str
    assert challenger["reset_fence"]["structural_reset_can_be_crossed"] is False


def test_branchless_lane_partial_evidence_also_vetoes_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lines = [
        _line(0, "Cho vay khách hàng", 40, 20, 400, 48),
        _line(1, "Theo đối tượng khách hàng", 590, 65, 900, 91),
        _line(2, "Loại hình doanh nghiệp", 600, 98, 890, 124),
        _line(3, "triệu đồng", 650, 135, 800, 161),
        _line(4, "Công ty TNHH", 60, 220, 450, 248),
        _line(5, "100", 680, 220, 760, 248),
        _line(6, "Công ty cổ phần khác", 60, 275, 500, 303),
        _line(7, "200", 680, 275, 760, 303),
    ]
    pages = [_page(1, lines)]
    semantic = semantic_region_module.build_accounting_semantic_region_graph_v1(
        pages,
        family12_graph_module._generic_spec(build_loan_enterprise_family12_spec_v1()),
    )
    semantic["regions"] = []
    semantic["near_regions"] = []
    semantic["metrics"]["branch_candidate_count"] = 0
    monkeypatch.setattr(
        family12_graph_module,
        "build_accounting_semantic_region_graph_v1",
        lambda _pages, _spec: copy.deepcopy(semantic),
    )

    result = build_loan_enterprise_family12_graph_v1(pages)

    assert result["bounded_absences"] == []
    challenger = result["branchless_rescue_challengers"][0]
    assert challenger["disposition"] == "UNRESOLVED"
    assert challenger["candidate_child_report_norm_ids"] == [768, 773]
    assert challenger["shared_scoped_table_binding"]["evidence_kind"] == ("UNRESOLVED_FRAGMENT")


def test_schema_parent_projection_is_exact_and_self_rehashed_tamper_fails_replay() -> None:
    foreign = "Cho vay tại chi nhánh và ngân hàng con nước ngoài"
    pages = [_page(1, _table_lines(rows=["Công ty TNHH", foreign]))]
    result = build_loan_enterprise_family12_graph_v1(pages)
    rows = {row["report_norm_id"]: row for row in result["regions"][0]["row_proposals"]}
    bindings = {item["report_norm_id"]: item for item in result["regions"][0]["binding_proposals"]}

    assert rows[768]["schema_parent_report_norm_id"] == 766
    assert rows[6058]["schema_parent_report_norm_id"] == 727
    assert bindings[768]["schema_parent_report_norm_id"] == 766
    assert bindings[6058]["schema_parent_report_norm_id"] == 727
    assert validate_loan_enterprise_family12_graph_replay_v1(result, pages) == result

    tampered = copy.deepcopy(result)
    tampered["regions"][0]["binding_proposals"][1]["schema_parent_report_norm_id"] = 766
    material = copy.deepcopy(tampered)
    material.pop("result_id")
    tampered["result_id"] = "lef12v1:result:" + family12_graph_module.canonical_json_sha256_v1(
        material
    )
    with pytest.raises(LoanEnterpriseFamily12GraphV1Error, match="does not replay exactly"):
        validate_loan_enterprise_family12_graph_replay_v1(tampered, pages)
