from __future__ import annotations

import copy

import pytest

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
    assert spec["safety"]["foreign_branch_or_subsidiary_allowed_report_norm_ids"] == [782]
    assert spec["safety"]["foreign_branch_or_subsidiary_forbidden_report_norm_ids"] == [
        765,
        6058,
    ]
    assert spec["safety"]["mapping_authority"] is False


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


@pytest.mark.parametrize(
    ("heading", "tier"),
    [
        (
            "Phân tích dư nợ cho vay theo đối turọng khách hàng và theo loại hình doanh nghiệp",
            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        ),
        (
            "Phân tích dư nợ cho vay theo đối trọng khách hàng và theo loại hình doanh nghiệp",
            "ONE_BASE_CHARACTER_EDIT_AFTER_ALL_EXACT_MISSES",
        ),
        (
            "Phân tích dư nợ cho vay theo đổi tượng khách hàng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTLESS_ALIAS",
        ),
        (
            "Phân tích dư nợ cho vay theo đối tượng khách hằng và theo loại hình doanh nghiệp",
            "EXACT_ACCENTLESS_ALIAS",
        ),
    ],
)
def test_branch_ocr_variants_use_exact_then_one_edit_only_on_miss(heading: str, tier: str) -> None:
    result = build_loan_enterprise_family12_graph_v1([_page(1, _table_lines(heading=heading))])

    assert result["regions"][0]["branch"]["match_tier"] == tier
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


def test_foreign_branch_component_binds_782_once_and_never_765_or_6058() -> None:
    foreign = "Cho vay tại chi nhánh và ngân hàng con nước ngoài"
    result = build_loan_enterprise_family12_graph_v1(
        [_page(1, _table_lines(rows=["Khác", foreign]))]
    )

    assert _binding_ids(result) == [782]
    assert set(_binding_ids(result)).isdisjoint({765, 6058})
    binding = result["regions"][0]["binding_proposals"][0]
    assert binding["foreign_branch_or_subsidiary_component"] is True
    assert _row_by_surface(result, foreign)["report_norm_id"] == 782
    assert _row_by_surface(result, "Khác")["status"] == (
        "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS"
    )


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
    second = _page(8, _table_lines()[1:])
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
