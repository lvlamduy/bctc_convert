from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_industry_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_industry_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
loan_industry = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = loan_industry
_SPEC.loader.exec_module(loan_industry)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 140, y + 24],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _four_lane_industry(*, reordered: bool = False) -> list[tuple[str, int, int]]:
    rows = [
        ("Nông nghiệp. lâm nghiệp và thủy sản", 10, "10", 20, "20"),
        ("Công nghiệp chế biến, chế tạo", 20, "20", 15, "15"),
        (
            "Sản xuất và phân phối điện, khí đốt và nước nóng, hơi nước và điều hòa không khí",
            5,
            "5",
            5,
            "5",
        ),
        ("Xây dựng", 15, "15", 10, "10"),
        (
            "Bán buôn và bán lẻ; sửa chữa mỏ tô, ô tô, xe máy và xe có động cơ khác",
            25,
            "25",
            30,
            "30",
        ),
        ("Hoạt động kinh doanh bất động sản", 25, "25", 20, "20"),
    ]
    if reordered:
        rows = [rows[5], rows[0], rows[3], rows[2], rows[4], rows[1]]
    result: list[tuple[str, int, int]] = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo ngành nghề kinh doanh", 0, 35),
        ("30/06/2026", 500, 75),
        ("31/12/2025", 900, 75),
        ("Triệu đồng", 500, 105),
        ("%", 700, 105),
        ("Triệu đồng", 900, 105),
        ("%", 1100, 105),
    ]
    for offset, (label, current, current_percent, previous, previous_percent) in enumerate(rows):
        y = 150 + offset * 48
        result.extend(
            [
                (label, 0, y),
                (str(current), 500, y),
                (current_percent, 700, y),
                (str(previous), 900, y),
                (previous_percent, 1100, y),
            ]
        )
    total_y = 150 + len(rows) * 48
    result.extend(
        [
            ("100", 500, total_y),
            ("100", 700, total_y),
            ("100", 900, total_y),
            ("100", 1100, total_y),
            ("Phân tích dư nợ theo loại hình doanh nghiệp", 0, total_y + 45),
        ]
    )
    return result


def _two_money_industry() -> list[tuple[str, int, int]]:
    rows = [
        ("Nông nghiệp, lâm nghiệp và thuỷ sản", 10, 9),
        ("Công nghiệp chế biến, chế tạo", 20, 18),
        ("Xây dựng", 30, 27),
        ("Vận tải kho bãi", 15, 14),
        ("Hoạt động tài chính và bảo hiểm", 5, 4),
        ("Khác", 20, 18),
    ]
    result: list[tuple[str, int, int]] = [
        ("Phân tích dư nợ cho vay theo ngành nghề đăng ký kinh doanh", 0, 0),
        ("Số cuối kỳ", 500, 40),
        ("Số đầu kỳ", 800, 40),
        ("Triệu VND", 500, 70),
        ("Triệu VND", 800, 70),
    ]
    for offset, (label, current, previous) in enumerate(rows):
        y = 115 + offset * 45
        result.extend([(label, 0, y), (str(current), 500, y), (str(previous), 800, y)])
    result.extend([("100", 500, 385), ("90", 800, 385)])
    return result


def _minimal_unique_child_subset(
    *, child_count: int = 2, parent_before_children: bool = True, reversed_children: bool = False
) -> list[tuple[str, int, int]]:
    rows = [
        ("Xây dựng", 30, 40),
        ("Vận tải kho bãi", 70, 60),
    ][:child_count]
    if reversed_children:
        rows.reverse()
    surfaces: list[tuple[str, int, int]] = []
    if parent_before_children:
        surfaces.append(("CHO VAY KHÁCH HÀNG", 0, 0))
    surfaces.extend(
        [
            ("Phân tích dư nợ cho vay theo ngành", 0, 35),
            ("30/06/2026", 500, 75),
            ("31/12/2025", 800, 75),
            ("Triệu đồng", 500, 105),
            ("Triệu đồng", 800, 105),
        ]
    )
    for offset, (label, current, previous) in enumerate(rows):
        y = 150 + offset * 48
        surfaces.extend([(label, 0, y), (str(current), 500, y), (str(previous), 800, y)])
    total_y = 150 + len(rows) * 48
    surfaces.extend(
        [
            (str(sum(item[1] for item in rows)), 500, total_y),
            (str(sum(item[2] for item in rows)), 800, total_y),
            ("Phân tích dư nợ theo loại hình doanh nghiệp", 0, total_y + 45),
        ]
    )
    if not parent_before_children:
        surfaces.append(("CHO VAY KHÁCH HÀNG", 0, total_y + 90))
    return surfaces


def test_variable_order_and_four_typed_lanes_form_one_bank_blind_graph() -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(_four_lane_industry(reordered=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    graph = result["graphs"][0]
    assert graph["branch"]["schema_concept"] == "PHAN_TICH_THEO_NGANH_NGHE_KINH_DOANH"
    assert graph["customer_loan_context"]["mode"] == "SAME_PAGE_CUSTOMER_LOAN_OWNER"
    assert graph["lane_types"] == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert [row["role"] for row in graph["rows"]] == [
        "REAL_ESTATE",
        "AGRICULTURE_FORESTRY_FISHERY",
        "CONSTRUCTION",
        "UTILITIES",
        "TRADE_REPAIR",
        "MANUFACTURING",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )
    assert result["safety"]["bank_filename_note_or_page_used_for_inference"] is False


@pytest.mark.parametrize("reversed_children", [False, True])
def test_parent_plus_two_children_is_enough_when_full_pdf_region_is_unique(
    reversed_children: bool,
) -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(_minimal_unique_child_subset(reversed_children=reversed_children))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert set(row["role"] for row in result["graphs"][0]["rows"]) == {
        "CONSTRUCTION",
        "TRANSPORT_STORAGE",
    }
    resolution = result["graphs"][0]["anchor_resolution"]
    assert resolution["selected_anchor_keys"] == [
        "PARENT:LOAN_INDUSTRY_CLASSIFICATION",
        "CHILD:TRANSPORT_STORAGE",
    ]
    assert resolution["selected_size"] == 2
    assert result["safety"]["minimum_child_anchor_count_with_recognized_parent"] == 1
    assert result["safety"]["minimum_total_anchor_combination_size"] == 2
    assert result["safety"]["pair_combinations_exhausted_before_triples"] is True
    assert result["safety"]["sibling_child_order_fixed"] is False
    assert result["safety"]["parent_precedes_descendants_required"] is True


def test_parent_plus_one_child_is_enough_when_the_full_pdf_region_is_unique() -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(_minimal_unique_child_subset(child_count=1))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert [row["role"] for row in result["graphs"][0]["rows"]] == ["CONSTRUCTION"]
    assert result["graphs"][0]["anchor_resolution"] == {
        "anchor_search_scope": "ALL_COMPLETE_AND_NEAR_BRANCH_REGIONS_IN_FULL_DOCUMENT",
        "child_priority_basis": "SEMANTIC_MONEY_MAGNITUDE_DISCOVERY_ONLY",
        "matching_region_count": 1,
        "pair_combinations_exhausted_before_triples": True,
        "selected_anchor_keys": [
            "PARENT:LOAN_INDUSTRY_CLASSIFICATION",
            "CHILD:CONSTRUCTION",
        ],
        "selected_size": 2,
        "status": "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
    }


def test_parent_without_any_child_anchor_is_not_a_family_region() -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(_minimal_unique_child_subset(child_count=0))]
    )

    assert result["graphs"] == []
    assert result["near_regions"][0]["unresolved_reasons"] == ["NO_LOAN_INDUSTRY_CHILD_ANCHOR"]


def _anchor_graph(roles: tuple[str, ...], values: tuple[int, ...]) -> dict[str, object]:
    return {
        "rows": [
            {
                "role": role,
                "values": [
                    {
                        "lane_type": "MONEY",
                        "semantic_surface": str(value),
                    }
                ],
            }
            for role, value in zip(roles, values, strict=True)
        ]
    }


def test_child_pair_is_used_only_after_all_parent_child_pairs_are_non_unique() -> None:
    graphs = [
        _anchor_graph(("AGRICULTURE_FORESTRY_FISHERY", "CONSTRUCTION"), (90, 80)),
        _anchor_graph(("AGRICULTURE_FORESTRY_FISHERY", "TRANSPORT_STORAGE"), (90, 70)),
        _anchor_graph(("CONSTRUCTION", "TRANSPORT_STORAGE"), (80, 70)),
    ]

    loan_industry._attach_minimal_anchor_resolution(graphs)

    assert graphs[0]["anchor_resolution"]["selected_anchor_keys"] == [
        "CHILD:AGRICULTURE_FORESTRY_FISHERY",
        "CHILD:CONSTRUCTION",
    ]
    assert graphs[0]["anchor_resolution"]["selected_size"] == 2


def test_pair_uniqueness_counts_near_regions_across_the_complete_pdf() -> None:
    graphs = [
        _anchor_graph(
            ("AGRICULTURE_FORESTRY_FISHERY", "CONSTRUCTION"),
            (90, 80),
        )
    ]
    near_regions = [
        {
            "matched_roles": ["AGRICULTURE_FORESTRY_FISHERY"],
        }
    ]

    loan_industry._attach_minimal_anchor_resolution(graphs, near_regions)

    assert graphs[0]["anchor_resolution"]["selected_anchor_keys"] == [
        "PARENT:LOAN_INDUSTRY_CLASSIFICATION",
        "CHILD:CONSTRUCTION",
    ]
    assert graphs[0]["anchor_resolution"]["matching_region_count"] == 1


def test_triple_is_used_only_when_every_two_anchor_combination_is_non_unique() -> None:
    a = "AGRICULTURE_FORESTRY_FISHERY"
    b = "CONSTRUCTION"
    c = "TRANSPORT_STORAGE"
    d = "MANUFACTURING"
    graphs = [
        _anchor_graph((a, b, c), (100, 90, 80)),
        _anchor_graph((a, b, d), (100, 90, 70)),
        _anchor_graph((a, c, d), (100, 80, 70)),
        _anchor_graph((b, c, d), (90, 80, 70)),
    ]

    loan_industry._attach_minimal_anchor_resolution(graphs)

    assert graphs[0]["anchor_resolution"]["selected_anchor_keys"] == [
        f"CHILD:{a}",
        f"CHILD:{b}",
        f"CHILD:{c}",
    ]
    assert graphs[0]["anchor_resolution"]["selected_size"] == 3


def test_explicit_industry_parent_can_replace_a_separate_customer_loan_owner() -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(_minimal_unique_child_subset(parent_before_children=False))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["graphs"][0]["customer_loan_context"]["mode"] == (
        "EXPLICIT_INDUSTRY_BRANCH_PARENT"
    )


def test_previous_page_customer_loan_owner_and_relative_periods_are_generic() -> None:
    pages = [
        _page([("5. CHO VAY KHÁCH HÀNG", 0, 0)], page_sequence=1),
        _page(_two_money_industry(), page_sequence=2),
    ]
    result = loan_industry.build_loan_industry_variant_graph_document_v1(pages)

    graph = result["graphs"][0]
    assert graph["customer_loan_context"]["mode"] == ("IMMEDIATE_PREVIOUS_PAGE_CUSTOMER_LOAN_OWNER")
    assert graph["period_mode"] == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert graph["lane_types"] == ["MONEY", "MONEY"]
    assert [item["semantic_surface"] for item in graph["total"]] == ["100", "90"]


def test_document_period_consensus_rescues_one_corrupted_local_year(monkeypatch) -> None:
    surfaces = _four_lane_industry()
    surfaces[2:4] = [
        ("Ngày 31 tháng 3", 500, 75),
        ("năm 2?26", 500, 100),
        ("Ngày 31 tháng 12", 900, 75),
        ("năm 2025", 900, 100),
    ]
    monkeypatch.setattr(
        loan_industry,
        "infer_document_reporting_period_context_v1",
        lambda _pages: {
            "balance_comparative_period_end": "31/12/2025",
            "current_period_end": "31/03/2026",
        },
    )

    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_annual_variants=True
    )

    graph = result["graphs"][0]
    assert graph["period_mode"] == ("DOCUMENT_PERIOD_CONTEXT_CORROBORATED_LOCAL_DAY_MONTH_HEADERS")
    assert [item["period"] for item in graph["period_axis"]] == [
        "31/03/2026",
        "31/12/2025",
    ]


def test_unrelated_prior_heading_does_not_override_explicit_industry_parent() -> None:
    surfaces = _four_lane_industry()
    surfaces[0] = ("TIỀN GỬI KHÁCH HÀNG", 0, 0)
    result = loan_industry.build_loan_industry_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["graphs"][0]["customer_loan_context"]["mode"] == (
        "EXPLICIT_INDUSTRY_BRANCH_PARENT"
    )


@pytest.mark.parametrize(
    "wrong_branch",
    [
        "Phân tích dư nợ theo loại hình doanh nghiệp",
        "Phân tích tiền gửi khách hàng theo ngành nghề kinh doanh",
        "Phân tích tài sản và nợ phải trả theo bộ phận kinh doanh",
    ],
)
def test_neighbour_families_are_negative_controls(wrong_branch: str) -> None:
    surfaces = _four_lane_industry()
    surfaces[1] = (wrong_branch, 0, 35)
    result = loan_industry.build_loan_industry_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["graphs"] == []


def test_two_complete_regions_fail_document_uniqueness() -> None:
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [
            _page(_four_lane_industry(), page_sequence=1),
            _page(_four_lane_industry(reordered=True), page_sequence=2),
        ]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"] == {
        "full_match_count": 2,
        "status": "AMBIGUOUS_MULTIPLE_FULL_MATCHES",
    }


def test_raw_bank_or_page_routing_fields_are_rejected() -> None:
    page = _page(_four_lane_industry())
    page["bank_code"] = "MBB"

    with pytest.raises(loan_industry.LoanIndustryVariantGraphV1Error, match="fields drifted"):
        loan_industry.build_loan_industry_variant_graph_document_v1([page])


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_four_lane_industry())]
    result = loan_industry.build_loan_industry_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "livgv1:result:" + loan_industry.canonical_json_sha256_v1(material)

    with pytest.raises(loan_industry.LoanIndustryVariantGraphV1Error, match="replay exactly"):
        loan_industry.validate_loan_industry_variant_graph_replay_v1(forged, pages)


def test_extended_annual_compact_branch_leading_owner_total_and_population_boundary() -> None:
    surfaces = [
        ("Theo ngành nghề kinh doanh", 0, 0),
        ("Số cuối năm", 500, 40),
        ("Số đầu năm", 800, 40),
        ("Triệu VND", 500, 70),
        ("Triệu VND", 800, 70),
        ("Cho vay khách hàng", 0, 105),
        ("100", 500, 105),
        ("90", 800, 105),
        ("Thương mại", 0, 150),
        ("60", 500, 150),
        ("55", 800, 150),
        ("Dịch vụ cá nhân và cộng đồng", 0, 195),
        ("40", 500, 195),
        ("35", 800, 195),
        ("Nghiệp vụ phát hành thư tín dụng trả chậm", 0, 240),
        ("Thương mại", 0, 285),
        ("5", 500, 285),
        ("4", 800, 285),
    ]

    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_annual_variants=True
    )

    graph = result["graphs"][0]
    assert graph["period_mode"] in {
        "LOCAL_RELATIVE_PERIOD_ROLES",
        "LOCAL_RELATIVE_YEAR_END_PERIOD_ROLES",
    }
    assert [row["role"] for row in graph["rows"]] == [
        "TRADE_REPAIR",
        "PERSONAL_COMMUNITY_SERVICES",
    ]
    assert [item["semantic_surface"] for item in graph["total"]] == ["100", "90"]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_extended_annual_suffix_and_detached_page_edge_noise_do_not_break_wrapped_label() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo ngành như sau:", 0, 35),
        ("31/12/2025", 500, 75),
        ("31/12/2024", 800, 75),
        ("Triệu đồng", 500, 105),
        ("Triệu đồng", 800, 105),
        ("Cung cấp nước, quản lý và xử lý rác thải,", 0, 150),
        ("PHÍ", 1500, 165),
        ("nước thải", 0, 175),
        ("10", 500, 175),
        ("9", 800, 175),
        ("Xây dựng", 0, 220),
        ("20", 500, 220),
        ("18", 800, 220),
        ("30", 500, 265),
        ("27", 800, 265),
    ]

    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        [_page(surfaces)], enable_extended_annual_variants=True
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert [row["role"] for row in result["graphs"][0]["rows"]] == [
        "WATER_WASTE",
        "CONSTRUCTION",
    ]


def test_extended_annual_replay_requires_the_same_variant_profile() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Theo ngành nghề kinh doanh", 0, 35),
        ("31/12/2025", 500, 75),
        ("31/12/2024", 800, 75),
        ("Triệu đồng", 500, 105),
        ("Triệu đồng", 800, 105),
        ("Thương mại", 0, 150),
        ("10", 500, 150),
        ("9", 800, 150),
        ("10", 500, 195),
        ("9", 800, 195),
    ]
    pages = [_page(surfaces)]
    result = loan_industry.build_loan_industry_variant_graph_document_v1(
        pages, enable_extended_annual_variants=True
    )

    assert (
        loan_industry.validate_loan_industry_variant_graph_replay_v1(
            result, pages, enable_extended_annual_variants=True
        )
        == result
    )
    with pytest.raises(loan_industry.LoanIndustryVariantGraphV1Error, match="replay exactly"):
        loan_industry.validate_loan_industry_variant_graph_replay_v1(result, pages)
