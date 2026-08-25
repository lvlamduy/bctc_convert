from __future__ import annotations

from bctc_ai.evaluation.accounting_family_row_axis_v1 import (
    build_accounting_family_row_axis_v1,
)
from bctc_ai.evaluation.accounting_family_topology_v1 import (
    build_accounting_family_topology_scan_v1,
    enumerate_accounting_family_role_occurrences_v1,
)
from bctc_ai.evaluation.accounting_minimal_unique_anchor_resolution_v1 import (
    build_accounting_minimal_unique_anchor_resolution_v1,
)
from bctc_ai.evaluation.loan_enterprise_family12_spec_v1 import (
    FAMILY_ID,
    build_loan_enterprise_family12_topology_spec_v1,
)


def _line(index: int, text: str, *, y: int | None = None) -> dict[str, object]:
    top = index * 30 if y is None else y
    return {
        "bbox": [40, top, 620, top + 22],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _page(surfaces: list[str], page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [_line(index, surface) for index, surface in enumerate(surfaces)],
        "page_sequence": page_sequence,
    }


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_family12_topology_spec_is_schema_free_shared_v4_data() -> None:
    spec = build_loan_enterprise_family12_topology_spec_v1()
    leaf_roles = {child["role"]: child for child in spec["children"]}

    assert spec["family_id"] == FAMILY_ID
    assert spec["format_version"] == "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V4"
    assert spec["parent"] == {
        "aliases": [
            "Cho vay khách hàng",
            "Cho vay khách hàng (tiếp theo)",
            "Các khoản cho vay khách hàng",
            "Dư nợ cho vay khách hàng",
            "Dư nợ cho vay khách hàng của Ngân hàng",
        ],
        "resolution_mode": "EXPLICIT_ONLY",
        "role": FAMILY_ID,
    }
    assert spec["limits"] == {
        "max_cluster_span_lines": 160,
        "max_continuation_pages": 1,
        "max_label_line_span": 3,
    }
    assert leaf_roles["ENTERPRISE_TYPE_BRANCH"]["role_kind"] == "STRUCTURAL_GROUP"
    assert leaf_roles["ECONOMIC_ORGANIZATION_LOANS_GROUP"]["role_kind"] == ("STRUCTURAL_GROUP")
    assert leaf_roles["CORE_LOAN_ENTERPRISE_SUBTOTAL"]["role_kind"] == "STRUCTURAL_GROUP"
    assert leaf_roles["EXPLICIT_LOAN_ENTERPRISE_TOTAL"]["role_kind"] == "TOTAL"
    foreign = leaf_roles["FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"]
    assert foreign["presence"] == "OPTIONAL"
    assert foreign["role_kind"] == "STRUCTURAL_GROUP"
    assert foreign["matchers"][0]["within_role"] == "ENTERPRISE_TYPE_BRANCH"
    assert foreign["matchers"][1]["within_role"] is None
    assert foreign["matchers"][1]["aliases"] == foreign["matchers"][0]["aliases"]
    assert "Cho vay tại chi nhánh và ngân hàng con nước ngoài" in foreign["matchers"][0]["aliases"]
    assert ["ENTERPRISE_TYPE_BRANCH", "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"] in spec[
        "required_role_combinations"
    ]
    assert len(spec["required_role_pools"]) == 1
    assert spec["required_role_pools"][0]["minimum_count"] == 2
    pool_roles = spec["required_role_pools"][0]["roles"]
    assert len(pool_roles) == 19
    assert {
        "STATE_ENTERPRISE_LOANS",
        "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS",
        "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS",
    } <= set(pool_roles)
    assert {
        "FOREIGN_BRANCH_ENTERPRISE_LOANS",
        "FOREIGN_BRANCH_INDIVIDUAL_LOANS",
    }.isdisjoint(pool_roles)
    assert "Các giao dịch với bên liên quan" in spec["hard_negative_aliases"]
    assert {
        "bank",
        "bank_code",
        "document_ordinal",
        "filename",
        "mapping_authority",
        "note",
        "numeric_authority",
        "page",
        "period",
        "report_norm_id",
        "schema_id",
        "unit",
    }.isdisjoint(_all_keys(spec))

    # The public builder never leaks its private mutable template.
    spec["children"][0]["role"] = "TAMPERED"
    assert build_loan_enterprise_family12_topology_spec_v1()["children"][0]["role"] == (
        "ENTERPRISE_TYPE_BRANCH"
    )


def test_family12_same_page_owner_branch_child_uses_pair_before_triple() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["observed_roles"] == [
        "ENTERPRISE_TYPE_BRANCH",
        "LIMITED_LIABILITY_COMPANY_LOANS",
    ]
    assert region["minimal_unique_anchor"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "selected_roles": [
            "PARENT:LOAN_ENTERPRISE_FAMILY12",
            "CHILD:ENTERPRISE_TYPE_BRANCH",
        ],
    }
    assert region["child_matches"][1]["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_child_can_continue_exactly_one_reset_free_page() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                ["Cho vay khách hàng", "Phân tích theo loại hình doanh nghiệp"],
                page_sequence=1,
            ),
            _page(["Công ty TNHH", "100"], page_sequence=2),
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["continuation_page_count"] == 1
    assert region["cluster_end_page_sequence_inclusive"] == 2
    company = next(
        item
        for item in region["child_matches"]
        if item["role"] == "LIMITED_LIABILITY_COMPANY_LOANS"
    )
    assert company["page_sequence"] == 2
    assert company["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_branch_before_wrapped_owner_uses_two_exact_context_free_leaves() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
                    "Dư nợ cho vay khách hàng của Ngân",
                    "hàng",
                    "Công ty Nhà nước",
                    "Công ty TNHH khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["parent_match"]["source_line_index"] == 1
    assert region["parent_match"]["end_source_line_index"] == 2
    assert region["observed_roles"] == [
        "STATE_ENTERPRISE_LOANS",
        "OTHER_LLC_LOANS",
    ]
    assert all(item["matched_within_role"] is None for item in region["child_matches"])


def test_family12_wrapped_state_majority_source_variants_resolve_exact_roles() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Công ty TNHH trên 1 Thành viên vốn Nhà",
                    "nước lớn hơn 50%",
                    "Công ty Cổ phần Vốn Nhà nước - 50%",
                    "(Nhà nước chiếm cổ phần chi phối)",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["observed_roles"] == [
        "STATE_MAJORITY_LLC_LOANS",
        "STATE_MAJORITY_JOINT_STOCK_COMPANY_LOANS",
    ]
    assert all(
        item["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
        for item in result["regions"][0]["child_matches"]
    )


def test_family12_branchless_owner_requires_two_distinct_exact_leaf_roles() -> None:
    spec = build_loan_enterprise_family12_topology_spec_v1()
    positive = build_accounting_family_topology_scan_v1(
        [_page(["Cho vay khách hàng", "Công ty TNHH khác", "Doanh nghiệp nhà nước"])],
        spec,
    )
    partial = build_accounting_family_topology_scan_v1(
        [_page(["Cho vay khách hàng", "Công ty TNHH khác"])],
        spec,
    )

    assert positive["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert positive["regions"][0]["observed_roles"] == [
        "OTHER_LLC_LOANS",
        "STATE_ENTERPRISE_LOANS",
    ]
    assert partial["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert partial["metrics"]["complete_region_count"] == 0


def test_family12_deposit_enterprise_table_without_loan_owner_is_not_observed() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "TIỀN GỬI CỦA KHÁCH HÀNG",
                    "Theo đối tượng khách hàng, loại hình doanh nghiệp",
                    "Công ty nhà nước",
                    "Công ty cổ phần khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["regions"] == []
    assert result["near_regions"] == []


def test_family12_nested_same_label_prefers_exact_contextual_source_child() -> None:
    pages = [
        _page(
            [
                "Cho vay khách hàng",
                "Cho vay các TCKT",
                "Công ty Nhà nước",
                "Cho vay cá nhân",
                "Hộ kinh doanh, cá nhân",
                "Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
                "Cho vay Doanh nghiệp",
                "Cho vay cá nhân",
            ]
        )
    ]
    spec = build_loan_enterprise_family12_topology_spec_v1()
    result = build_accounting_family_topology_scan_v1(pages, spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    occurrences = enumerate_accounting_family_role_occurrences_v1(pages, spec, result["regions"][0])
    by_role = {}
    for occurrence in occurrences:
        by_role.setdefault(occurrence["role"], []).append(occurrence)
    assert [item["source_line_index"] for item in by_role["ECONOMIC_ORGANIZATION_LOANS_GROUP"]] == [
        1
    ]
    assert [item["source_line_index"] for item in by_role["INDIVIDUAL_LOANS_GROUP"]] == [3]
    assert by_role["FOREIGN_BRANCH_ENTERPRISE_LOANS"][0]["matched_within_role"] == (
        "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"
    )
    assert by_role["FOREIGN_BRANCH_INDIVIDUAL_LOANS"][0]["matched_within_role"] == (
        "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"
    )


def test_family12_reset_fenced_span_retains_a_known_long_same_table_child() -> None:
    surfaces = [
        "Cho vay khách hàng",
        "Phân tích theo loại hình doanh nghiệp",
        *[f"Dòng nội dung trong cùng bảng {ordinal}" for ordinal in range(105)],
        "Công ty TNHH",
    ]

    result = build_accounting_family_topology_scan_v1(
        [_page(surfaces)],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    company = next(
        item
        for item in result["regions"][0]["child_matches"]
        if item["role"] == "LIMITED_LIABILITY_COMPANY_LOANS"
    )
    assert company["source_line_index"] == 107
    assert company["source_line_index"] > 96


def test_family12_reset_budget_and_partial_topologies_fail_closed() -> None:
    spec = build_loan_enterprise_family12_topology_spec_v1()
    reset = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Phân tích theo ngành nghề kinh doanh",
                    "Công ty TNHH",
                ]
            )
        ],
        spec,
    )
    beyond_budget = build_accounting_family_topology_scan_v1(
        [
            _page(
                ["Cho vay khách hàng", "Phân tích theo loại hình doanh nghiệp"],
                page_sequence=1,
            ),
            _page(["Nội dung không thuộc bảng"], page_sequence=2),
            _page(["Công ty TNHH"], page_sequence=3),
        ],
        spec,
    )
    partial = build_accounting_family_topology_scan_v1(
        [_page(["Cho vay khách hàng", "Phân tích theo loại hình doanh nghiệp"])],
        spec,
    )

    for result in (reset, beyond_budget, partial):
        assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
        assert result["metrics"]["complete_region_count"] == 0
        assert result["near_regions"]
        assert result["near_regions"][0]["unresolved_reasons"][0].startswith(
            "MISSING_REQUIRED_ROLE_COMBINATION:"
        )


def test_family12_two_independent_equal_targets_remain_unresolved() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                    "Phân tích theo ngành nghề kinh doanh",
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    assert result["metrics"]["complete_region_count"] == 2
    assert result["uniqueness"]["minimal_role_combination_proved"] is False
    assert all(region["minimal_unique_anchor"] is None for region in result["regions"])


def test_family12_distinct_targets_require_shared_pair_controls_before_triples() -> None:
    topology = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                    "Phân tích theo ngành nghề kinh doanh",
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Doanh nghiệp nhà nước",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert topology["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    assert topology["metrics"]["complete_region_count"] == 2
    candidates = [
        {
            "candidate_id": "complete-company",
            "child_anchor_ids": [
                "ENTERPRISE_TYPE_BRANCH",
                "LIMITED_LIABILITY_COMPANY_LOANS",
            ],
            "disposition": "COMPLETE",
            "parent_anchor_id": "LOAN_ENTERPRISE_FAMILY12",
        },
        {
            "candidate_id": "complete-state",
            "child_anchor_ids": [
                "ENTERPRISE_TYPE_BRANCH",
                "STATE_ENTERPRISE_LOANS",
            ],
            "disposition": "COMPLETE",
            "parent_anchor_id": "LOAN_ENTERPRISE_FAMILY12",
        },
        {
            "candidate_id": "near-owner-company",
            "child_anchor_ids": ["LIMITED_LIABILITY_COMPANY_LOANS"],
            "disposition": "NEAR",
            "parent_anchor_id": "LOAN_ENTERPRISE_FAMILY12",
        },
        {
            "candidate_id": "near-branch-company",
            "child_anchor_ids": [
                "ENTERPRISE_TYPE_BRANCH",
                "LIMITED_LIABILITY_COMPANY_LOANS",
            ],
            "disposition": "NEAR",
            "parent_anchor_id": None,
        },
        {
            "candidate_id": "near-owner-state",
            "child_anchor_ids": ["STATE_ENTERPRISE_LOANS"],
            "disposition": "NEAR",
            "parent_anchor_id": "LOAN_ENTERPRISE_FAMILY12",
        },
        {
            "candidate_id": "near-branch-state",
            "child_anchor_ids": ["ENTERPRISE_TYPE_BRANCH", "STATE_ENTERPRISE_LOANS"],
            "disposition": "NEAR",
            "parent_anchor_id": None,
        },
    ]
    resolution = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates,
        document_scope_id="family12-two-distinct-targets",
    )
    complete = {
        item["candidate_id"]: item["resolution"]
        for item in resolution["candidates"]
        if item["disposition"] == "COMPLETE"
    }

    assert complete["complete-company"]["selected_anchor_ids"] == [
        "LOAN_ENTERPRISE_FAMILY12",
        "ENTERPRISE_TYPE_BRANCH",
        "LIMITED_LIABILITY_COMPANY_LOANS",
    ]
    assert complete["complete-state"]["selected_anchor_ids"] == [
        "LOAN_ENTERPRISE_FAMILY12",
        "ENTERPRISE_TYPE_BRANCH",
        "STATE_ENTERPRISE_LOANS",
    ]
    assert all(item["selected_size"] == 3 for item in complete.values())
    assert all(item["searched_pair_count"] == 3 for item in complete.values())
    assert all(item["pair_combinations_exhausted_before_triples"] for item in complete.values())


def _axis_line(
    ordinal: int,
    semantic: str,
    numeric: str,
    bbox: list[int],
) -> dict[str, object]:
    sample = ordinal + 1
    return {
        "bbox": bbox,
        "crop_ref": {
            "path": f"opaque/family12-{sample:04d}.png",
            "sha256": f"{sample:064x}",
            "size_bytes": 100 + sample,
        },
        "line_ordinal": ordinal,
        "numeric_recognition": {"raw_prediction": numeric, "reader_score": 0.95},
        "sample_id": f"family12-sample-{sample:04d}",
        "vietocr_text": semantic,
    }


def test_family12_topology_spec_is_consumed_by_shared_row_axis_without_authority() -> None:
    pages = [
        {
            "lines": [
                _axis_line(0, "Cho vay khách hàng", "", [30, 20, 430, 42]),
                _axis_line(1, "31.12.2025", "31.12.2025", [600, 50, 700, 72]),
                _axis_line(2, "31.12.2024", "31.12.2024", [800, 50, 900, 72]),
                _axis_line(
                    3,
                    "Phân tích theo loại hình doanh nghiệp",
                    "",
                    [40, 80, 500, 102],
                ),
                _axis_line(4, "Công ty TNHH", "", [60, 130, 360, 152]),
                _axis_line(5, "100", "100", [600, 130, 700, 152]),
                _axis_line(6, "90", "90", [800, 130, 900, 152]),
            ],
            "page_sequence": 1,
            "page_width": 1000,
        }
    ]

    result = build_accounting_family_row_axis_v1(
        pages, build_loan_enterprise_family12_topology_spec_v1()
    )

    assert result["topology_status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["status"] == "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY"
    assert [row["role"] for row in result["rows"]] == ["LIMITED_LIABILITY_COMPANY_LOANS"]
    assert [value["raw_prediction"] for value in result["rows"][0]["values"]] == ["100", "90"]
    assert result["safety"]["mapping_authority"] is False
    assert result["safety"]["numeric_authority"] is False
