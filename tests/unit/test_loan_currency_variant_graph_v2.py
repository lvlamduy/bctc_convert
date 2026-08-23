from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1
from bctc_ai.evaluation import accounting_hierarchical_table_closure_v1 as hierarchy_v1
from scripts.experiments.loan_currency_variant_graph_v2 import (
    FAMILY_ID,
    LOAN_CURRENCY_EVALUATION_SPEC_V2,
    LOAN_CURRENCY_HIERARCHY_SPEC_V2,
    LOAN_CURRENCY_TOPOLOGY_SPEC_V2,
    LoanCurrencyVariantGraphV2Error,
    build_loan_currency_topology_scan_v2,
    validate_loan_currency_topology_scan_replay_v2,
)


def _page(lines: list[str], *, page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [20, 20 + ordinal * 30, 900, 42 + ordinal * 30],
                "source_line_index": ordinal,
                "source_text": None,
                "vietocr_text": text,
            }
            for ordinal, text in enumerate(lines)
        ],
        "page_sequence": page_sequence,
    }


def _scan(lines: list[str]) -> dict[str, object]:
    return build_loan_currency_topology_scan_v2([_page(lines)])


def test_acb_qualified_pair_is_one_explicit_pair_first_region() -> None:
    result = _scan(
        [
            "CHO VAY KHÁCH HÀNG (TIẾP THEO)",
            "Phân tích dư nợ theo loại tiền tệ",
            "Cho vay bằng VND",
            "100",
            "Cho vay bằng ngoại tệ và vàng",
            "20",
            "120",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["metrics"]["complete_region_count"] == 1
    region = result["regions"][0]
    assert region["observed_roles"] == [
        "VND_LOANS",
        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
    ]
    assert region["minimal_unique_anchor"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "selected_roles": [
            "PARENT:LOAN_CURRENCY_BRANCH",
            "CHILD:VND_LOANS",
        ],
    }


def test_hdb_repeated_generic_labels_bind_to_their_structural_groups() -> None:
    result = _scan(
        [
            "Phân tích dư nợ theo loại hình tiền tệ",
            "Cho vay khách hàng",
            "Bằng VND",
            "100",
            "Bằng ngoại tệ",
            "20",
            "Nghiệp vụ phát hành thư tín dụng trả chậm",
            "phát sinh trước ngày 01 tháng 7 năm 2024",
            "Bằng VND",
            "-",
            "Bằng ngoại tệ",
            "5",
            "125",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = result["regions"][0]["child_matches"]
    assert [(item["role"], item["matched_within_role"]) for item in matches] == [
        ("CORE_TOTAL_GROUP", None),
        ("VND_LOANS", "CORE_TOTAL_GROUP"),
        ("FOREIGN_CURRENCY_AND_GOLD_LOANS", "CORE_TOTAL_GROUP"),
        ("DEFERRED_LC_PRE_2024_GROUP", None),
        ("DEFERRED_LC_VND", "DEFERRED_LC_PRE_2024_GROUP"),
        ("DEFERRED_LC_FOREIGN", "DEFERRED_LC_PRE_2024_GROUP"),
    ]
    lc_group = next(item for item in matches if item["role"] == "DEFERRED_LC_PRE_2024_GROUP")
    assert (lc_group["source_line_index"], lc_group["end_source_line_index"]) == (6, 7)


def test_wrapped_group_uses_geometry_when_provider_order_interleaves_total_cell() -> None:
    texts_and_boxes = [
        ("Phân tích dư nợ theo loại hình tiền tệ", [20, 20, 500, 42]),
        ("Cho vay khách hàng", [20, 70, 300, 92]),
        ("Bằng VND", [40, 100, 240, 122]),
        ("100", [650, 100, 730, 122]),
        ("Bằng ngoại tệ", [40, 130, 260, 152]),
        ("20", [650, 130, 730, 152]),
        ("Nghiệp vụ phát hành thư tín dụng trả chậm", [20, 180, 530, 202]),
        ("5", [650, 180, 730, 202]),
        ("phát sinh trước ngày 01 tháng 7 năm 2024", [20, 207, 540, 229]),
        ("Bằng VND", [40, 245, 240, 267]),
        ("-", [650, 245, 730, 267]),
        ("Bằng ngoại tệ", [40, 275, 260, 297]),
        ("5", [650, 275, 730, 297]),
    ]
    page = {
        "lines": [
            {
                "bbox": bbox,
                "source_line_index": ordinal,
                "source_text": None,
                "vietocr_text": text,
            }
            for ordinal, (text, bbox) in enumerate(texts_and_boxes)
        ],
        "page_sequence": 1,
    }

    result = build_loan_currency_topology_scan_v2([page])

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    group = next(
        item
        for item in result["regions"][0]["child_matches"]
        if item["role"] == "DEFERRED_LC_PRE_2024_GROUP"
    )
    assert group["source_line_indices"] == [6, 8]
    assert group["surface"].endswith("ngày 01 tháng 7 năm 2024")


@pytest.mark.parametrize(
    "cutoff",
    ["01/07/2024", "1/7/2024", "01-07-2024", "1.7.2024"],
)
def test_regulatory_population_cutoff_accepts_equivalent_date_surfaces(cutoff: str) -> None:
    result = _scan(
        [
            "Phân tích dư nợ theo loại hình tiền tệ",
            "Cho vay khách hàng",
            "Bằng VND",
            "100",
            "Bằng ngoại tệ",
            "20",
            f"Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày {cutoff}",
            "Bằng VND",
            "-",
            "Bằng ngoại tệ",
            "5",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = result["regions"][0]["child_matches"]
    group = next(item for item in matches if item["role"] == "DEFERRED_LC_PRE_2024_GROUP")
    assert group["surface"].endswith(cutoff)
    assert [
        item["role"]
        for item in matches
        if item["matched_within_role"] == "DEFERRED_LC_PRE_2024_GROUP"
    ] == ["DEFERRED_LC_VND", "DEFERRED_LC_FOREIGN"]


def test_truncated_deferred_lc_phrase_does_not_create_a_source_population() -> None:
    result = _scan(
        [
            "Phân tích dư nợ theo loại hình tiền tệ",
            "Cho vay khách hàng",
            "Bằng VND",
            "100",
            "Bằng ngoại tệ",
            "20",
            "Nghiệp vụ phát hành thư tín dụng trả chậm",
            "Bằng VND",
            "-",
            "Bằng ngoại tệ",
            "5",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    roles = {item["role"] for item in result["regions"][0]["child_matches"]}
    assert "DEFERRED_LC_PRE_2024_GROUP" not in roles
    assert "DEFERRED_LC_VND" not in roles
    assert "DEFERRED_LC_FOREIGN" not in roles


def test_reordered_qualified_children_are_permitted() -> None:
    result = _scan(
        [
            "Theo loại tiền tệ",
            "Cho vay bằng ngoại tệ",
            "20",
            "Cho vay bằng đồng Việt Nam",
            "100",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["metrics"]["reordered_complete_region_count"] == 1
    assert result["regions"][0]["observed_roles"] == [
        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
        "VND_LOANS",
    ]


def test_loose_currency_pair_without_explicit_branch_is_not_a_positive() -> None:
    result = _scan(["Bằng VND", "100", "Bằng ngoại tệ", "20"])

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["regions"] == []


def test_interest_rate_family_inside_candidate_is_a_negative_control() -> None:
    result = _scan(
        [
            "Phân tích dư nợ theo loại tiền tệ",
            "Rủi ro lãi suất",
            "Cho vay bằng VND",
            "100",
            "Cho vay bằng ngoại tệ",
            "20",
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []
    assert result["metrics"]["near_region_count"] == 1


def test_next_industry_family_is_an_exact_structural_boundary() -> None:
    result = _scan(
        [
            "Phân tích dư nợ theo loại tiền tệ",
            "Cho vay bằng VND",
            "100",
            "Cho vay bằng ngoại tệ",
            "20",
            "120",
            "Theo ngành nghề kinh doanh",
            "Nông nghiệp",
            "1",
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["cluster_end_source_line_index_exclusive"] == 6


def test_specs_are_schema_free_and_compile_against_generic_v3_contracts() -> None:
    compiled = topology_v1._spec(LOAN_CURRENCY_TOPOLOGY_SPEC_V2)
    hierarchy = hierarchy_v1._spec(LOAN_CURRENCY_HIERARCHY_SPEC_V2, LOAN_CURRENCY_TOPOLOGY_SPEC_V2)

    assert compiled["family_id"] == FAMILY_ID
    assert compiled["parent"]["resolution_mode"] == "EXPLICIT_ONLY"
    assert compiled["required_role_combinations"] == [
        ["VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"]
    ]
    assert hierarchy["family_id"] == FAMILY_ID
    assert LOAN_CURRENCY_EVALUATION_SPEC_V2["expected_lane_unit_kinds"] == [
        "MONEY",
        "MONEY",
    ]
    forbidden_keys = {
        "bank",
        "bank_code",
        "document_ordinal",
        "filename",
        "note",
        "page",
        "report_norm_id",
        "schema_id",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value), set())
        return set()

    assert keys(LOAN_CURRENCY_TOPOLOGY_SPEC_V2).isdisjoint(forbidden_keys)
    assert keys(LOAN_CURRENCY_HIERARCHY_SPEC_V2).isdisjoint(forbidden_keys)


def test_exact_replay_rejects_tampered_scan() -> None:
    pages = [
        _page(
            [
                "Phân tích dư nợ theo loại tiền tệ",
                "Cho vay bằng VND",
                "100",
                "Cho vay bằng ngoại tệ",
                "20",
            ]
        )
    ]
    result = build_loan_currency_topology_scan_v2(pages)

    assert validate_loan_currency_topology_scan_replay_v2(result, pages) == result
    tampered = copy.deepcopy(result)
    tampered["metrics"]["complete_region_count"] = 2
    with pytest.raises(LoanCurrencyVariantGraphV2Error):
        validate_loan_currency_topology_scan_replay_v2(tampered, pages)
