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
        "max_cluster_span_lines": 256,
        "max_continuation_pages": 1,
        "max_label_line_span": 6,
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
    assert "Dư nợ tại chi nhánh nước ngoài" in foreign["matchers"][0]["aliases"]
    margin = leaf_roles["MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS"]
    assert (
        "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch đầu tư "
        "chứng khoán" in margin["matchers"][0]["aliases"]
    )
    assert margin["matchers"][0]["allow_trailing_organization_qualifier"] is True
    assert (
        "Các khoản cho vay margin chứng khoán và ứng trước khách hàng"
        in margin["matchers"][0]["aliases"]
    )
    other = leaf_roles["OTHER_ENTERPRISE_LOANS"]
    assert other["matchers"] == [
        {
            "aliases": ["Khác", "Thành phần kinh tế khác"],
            "within_role": "ENTERPRISE_TYPE_BRANCH",
        },
        {
            "aliases": ["Thành phần kinh tế khác"],
            "within_role": None,
        },
        {
            "aliases": ["Khác"],
            "presence_anchor": False,
            "within_role": None,
        },
    ]
    assert ["ENTERPRISE_TYPE_BRANCH", "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS"] in spec[
        "required_role_combinations"
    ]
    assert len(spec["required_role_pools"]) == 1
    assert spec["required_role_pools"][0]["minimum_count"] == 2
    pool_roles = spec["required_role_pools"][0]["roles"]
    assert len(pool_roles) == 23
    assert {
        "STATE_ENTERPRISE_LOANS",
        "FOREIGN_BRANCH_OR_SUBSIDIARY_LOANS",
        "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS",
        "SOURCE_ONLY_MIXED_LEGAL_FORM_LOANS",
        "SOURCE_ONLY_UNQUALIFIED_COOPERATIVE_LOANS",
        "SOURCE_ONLY_PERSON_LOANS",
        "SOURCE_ONLY_OTHER_CUSTOMER_OBJECT_LOANS",
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


def test_family12_two_page_budget_keeps_late_contextual_other_row() -> None:
    first_page = ["Cho vay khách hàng", *[f"Nội dung {index}" for index in range(85)]]
    second_page = [
        "Phân tích dư nợ cho vay khách hàng theo đối tượng khách hàng và theo loại hình doanh nghiệp như sau",
        *[f"Dòng trình bày {index}" for index in range(80)],
        "Khác",
    ]

    result = build_accounting_family_topology_scan_v1(
        [_page(first_page, page_sequence=1), _page(second_page, page_sequence=2)],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["continuation_page_count"] == 1
    other = next(
        item for item in region["child_matches"] if item["role"] == "OTHER_ENTERPRISE_LOANS"
    )
    assert other["page_sequence"] == 2
    assert other["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_bare_other_is_not_a_context_free_presence_anchor() -> None:
    result = build_accounting_family_topology_scan_v1(
        [_page(["Cho vay khách hàng", "Khác"])],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert result["near_regions"][0]["observed_roles"] == ["OTHER_ENTERPRISE_LOANS"]


def test_family12_explicit_other_wording_remains_a_context_free_role() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Thành phần kinh tế khác",
                    "Công ty TNHH",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["observed_roles"] == [
        "OTHER_ENTERPRISE_LOANS",
        "LIMITED_LIABILITY_COMPANY_LOANS",
    ]
    assert all(
        item["matched_within_role"] is None for item in result["regions"][0]["child_matches"]
    )


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


def test_family12_abbreviated_multiple_member_state_majority_label_resolves_exact_role() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Theo đối tượng khách hàng",
                    "Công ty TNHH hơn MTV vốn Nhà nước trên 50%",
                    "Công ty Nhà nước",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    majority = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "STATE_MAJORITY_LLC_LOANS"
    )
    assert majority["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert majority["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_wrapped_mtv_with_state_capital_label_resolves_exact_role() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
                    "Công ty TNHH MTV với vốn Nhà nước",
                    "trên 50%",
                    "Công ty Nhà nước",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    majority = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "STATE_MAJORITY_LLC_LOANS"
    )
    assert majority["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert majority["source_line_index"] == 2
    assert majority["end_source_line_index"] == 3
    assert majority["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_exact_sibling_headings_fence_contextual_customer_object_rows() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Theo loại hình cho vay",
                    "Cho vay giao dịch ký quỹ",
                    "Phân tích dư nợ theo thời gian cho vay gốc",
                    "Phân tích dư nợ theo ngành nghề kinh doanh",
                    "Theo đối tượng khách hàng",
                    "Doanh nghiệp nhà nước",
                    "Doanh nghiệp có vốn đầu tư nước ngoài",
                    "Công ty cổ phần, công ty trách nhiệm hữu hạn và doanh nghiệp khác",
                    "Hợp tác xã",
                    "Cá nhân",
                    "Các đối tượng khác",
                    "Theo chất lượng nợ cho vay",
                    "Cho vay giao dịch ký quỹ",
                    "Theo kỳ hạn",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    by_role = {item["role"]: item for item in region["child_matches"]}
    assert by_role["STATE_ENTERPRISE_LOANS"]["matched_within_role"] == ("ENTERPRISE_TYPE_BRANCH")
    assert by_role["FOREIGN_INVESTED_COMPANY_LOANS"]["matched_within_role"] == (
        "ENTERPRISE_TYPE_BRANCH"
    )
    assert by_role["SOURCE_ONLY_MIXED_LEGAL_FORM_LOANS"]["matched_within_role"] == (
        "ENTERPRISE_TYPE_BRANCH"
    )
    assert by_role["SOURCE_ONLY_UNQUALIFIED_COOPERATIVE_LOANS"]["matched_within_role"] == (
        "ENTERPRISE_TYPE_BRANCH"
    )
    assert by_role["SOURCE_ONLY_PERSON_LOANS"]["matched_within_role"] == ("ENTERPRISE_TYPE_BRANCH")
    assert by_role["SOURCE_ONLY_OTHER_CUSTOMER_OBJECT_LOANS"]["matched_within_role"] == (
        "ENTERPRISE_TYPE_BRANCH"
    )
    margin = [
        item
        for item in region["child_matches"]
        if item["role"] == "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS"
    ]
    assert len(margin) == 1
    assert margin[0]["source_line_index"] == 2
    assert margin[0]["matched_within_role"] is None
    assert {
        "LOAN_TYPE_PRESENTATION_BRANCH",
        "LOAN_QUALITY_PRESENTATION_BRANCH",
        "LOAN_MATURITY_PRESENTATION_BRANCH",
        "LOAN_ORIGINAL_TERM_PRESENTATION_BRANCH",
        "LOAN_INDUSTRY_PRESENTATION_BRANCH",
    } <= set(region["observed_roles"])


def test_family12_six_line_state_majority_source_label_resolves_exact_role() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Công ty cổ phần có vốn góp của",
                    "Nhà nước trên 50% vốn điều lệ",
                    "hoặc tổng số cổ phần có quyền",
                    "biểu quyết, hoặc nhà nước giữ",
                    "quyền chi phối trong Điều lệ của",
                    "công ty",
                    "Công ty Nhà nước",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    majority = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "STATE_MAJORITY_JOINT_STOCK_COMPANY_LOANS"
    )
    assert majority["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert majority["source_line_index"] == 1
    assert majority["end_source_line_index"] == 6


def test_family12_six_line_state_majority_control_clause_resolves_exact_role() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
                    "Công ty cổ phần có vốn góp của",
                    "Nhà nước trên 50% vốn điều lệ",
                    "hoặc tổng số cổ phần có quyền",
                    "biểu quyết, hoặc Nhà nước giữ",
                    "quyền chi phối đối với công ty trong",
                    "Điều lệ của công ty",
                    "Công ty cổ phần khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    majority = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "STATE_MAJORITY_JOINT_STOCK_COMPANY_LOANS"
    )
    assert majority["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert majority["source_line_index"] == 2
    assert majority["end_source_line_index"] == 7
    assert majority["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_state_control_clause_under_deposit_parent_is_not_observed() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi của khách hàng",
                    "Phân tích tiền gửi khách hàng theo loại hình doanh nghiệp",
                    "Công ty cổ phần có vốn góp của",
                    "Nhà nước trên 50% vốn điều lệ",
                    "hoặc tổng số cổ phần có quyền",
                    "biểu quyết, hoặc Nhà nước giữ",
                    "quyền chi phối đối với công ty trong",
                    "Điều lệ của công ty",
                    "Công ty cổ phần khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["metrics"]["complete_region_count"] == 0


def test_family12_wrapped_state_majority_equity_prefix_avoids_ocr_only_tail() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Công ty có phân có vốn cổ phần của nhà",
                    "nước chiếm trên 50% vộn điều lệ hoặc tổng",
                    "số cổ phân có quyền biểu quyết, hoặc nhà",
                    "nước giữ quyền chi phối đổi với công ty",
                    "trong Điều lệ của công ly",
                    "Công ty cổ phần khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    majority = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "STATE_MAJORITY_JOINT_STOCK_COMPANY_LOANS"
    )
    assert majority["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert majority["source_line_index"] == 1
    assert majority["end_source_line_index"] == 4


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
        *[f"Dòng nội dung trong cùng bảng {ordinal}" for ordinal in range(220)],
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
    assert company["source_line_index"] == 222
    assert company["source_line_index"] > 192


def test_family12_wrapped_margin_vpbanks_variant_is_one_exact_contextual_child() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                    "Các khoản cho vay giao dịch ký quỹ và ứng",
                    "trước cho khách hàng giao dịch đầu tư chứng",
                    "khoán tại VPBankS",
                    "Khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    margin = [
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS"
    ]
    assert len(margin) == 1
    assert margin[0]["match_kind"] == (
        "EXACT_ACCENTLESS_ALIAS_WITH_TRAILING_ORGANIZATION_QUALIFIER"
    )
    assert margin[0]["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"
    assert margin[0]["source_line_index"] == 3
    assert margin[0]["end_source_line_index"] == 5


def test_family12_margin_phrase_accepts_one_bounded_organization_qualifier() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                    "Các khoản cho vay margin chứng khoán",
                    "và ứng trước khách hàng tại MB?",
                    "Khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    margin = next(
        match
        for match in result["regions"][0]["child_matches"]
        if match["role"] == "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS"
    )
    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert margin["match_kind"] == ("EXACT_ACCENTLESS_ALIAS_WITH_TRAILING_ORGANIZATION_QUALIFIER")
    assert margin["matched_within_role"] == "ENTERPRISE_TYPE_BRANCH"


def test_family12_margin_organization_qualifier_does_not_admit_semantic_suffix() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Phân tích theo loại hình doanh nghiệp",
                    "Công ty TNHH",
                    "Các khoản cho vay giao dịch ký quỹ và ứng trước cho khách hàng giao dịch "
                    "đầu tư chứng khoán tại không bao gồm khách hàng",
                    "Khác",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert "MARGIN_AND_SECURITIES_SALE_ADVANCE_LOANS" not in result["regions"][0]["observed_roles"]


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


def test_family12_next_note_heading_fences_unrelated_totals_after_visible_table_total() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng (tiếp theo)",
                    "Phân tích dư nợ theo đối tượng khách hàng, loại hình doanh nghiệp",
                    "Công ty nhà nước",
                    "Công ty TNHH khác",
                    "381.972.016 100,00 324.009.713 100,00",
                    "10. DỰ PHÒNG RÙI RO CHO VAY KHÁCH HÀNG",
                    "Tổng cộng",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["cluster_end_document_line_ordinal_exclusive"] == 5
    assert "EXPLICIT_LOAN_ENTERPRISE_TOTAL" not in region["observed_roles"]


def test_family12_letter_of_credit_subtable_fences_repeated_enterprise_labels() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Cho vay khách hàng",
                    "Công ty trách nhiệm hữu hạn khác",
                    "228.506.157 155.438.528",
                    "Hộ kinh doanh, cá nhân",
                    "167.684.870 159.619.463",
                    "Công ty Cổ phần khác",
                    "139.883.573 109.598.655",
                    "Nghiệp vụ phát hành thư tín dụng trả chậm",
                    "phát sinh trước ngày 01 tháng 7 năm 2024",
                    "Công ty Cổ phần khác",
                    "0 6.363.484",
                    "Công ty trách nhiệm hữu hạn khác",
                    "0 4.815.288",
                ]
            )
        ],
        build_loan_enterprise_family12_topology_spec_v1(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["cluster_end_document_line_ordinal_exclusive"] == 7
    assert [item["source_line_index"] for item in region["child_matches"]] == [1, 3, 5]


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
