from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    AccountingFamilyTopologyV1Error,
    build_accounting_family_topology_scan_v1,
    enumerate_accounting_family_role_occurrences_v1,
    validate_accounting_family_topology_scan_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]


def _line(
    index: int,
    text: str,
    *,
    source_text: str | None = None,
    x: int = 20,
    y: int | None = None,
) -> dict[str, object]:
    top = index * 30 if y is None else y
    return {
        "bbox": [x, top, x + 360, top + 22],
        "source_line_index": index,
        "source_text": source_text,
        "vietocr_text": text,
    }


def _page(surfaces: list[str], page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [_line(index, text) for index, text in enumerate(surfaces)],
        "page_sequence": page_sequence,
    }


def test_exact_source_bound_text_challenger_can_rescue_one_vietocr_label() -> None:
    page = _page(
        [
            "Phân tích dư nợ theo thời gian",
            "Nợ ngắn hạn",
            "Nội dung OCR sai",
        ]
    )
    page["lines"][2]["source_text"] = "Nợ trung hạn"

    result = build_accounting_family_topology_scan_v1([page], _generic_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    medium = next(
        match for match in result["regions"][0]["child_matches"] if match["role"] == "MEDIUM_TERM"
    )
    assert medium["surface"] == "Nợ trung hạn"
    assert medium["match_kind"] == "EXACT_ACCENTLESS_BOUND_SOURCE_TEXT_CHALLENGER_ALIAS"
    assert result["safety"][
        "source_bound_text_challenger_requires_exact_alias_and_complete_topology"
    ]


def test_source_bound_text_challenger_does_not_use_fuzzy_alias_matching() -> None:
    page = _page(
        [
            "Phân tích dư nợ theo thời gian",
            "Nợ ngắn hạn",
            "Nội dung OCR sai",
        ]
    )
    page["lines"][2]["source_text"] = "Nợ trun hạn"

    result = build_accounting_family_topology_scan_v1([page], _generic_spec())

    assert result["status"] != "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"


def test_geometry_joins_wrapped_label_around_interleaved_numeric_cells() -> None:
    page = {
        "lines": [
            _line(0, "Phân tích dư nợ theo thời gian", y=20),
            _line(1, "Nợ", x=50, y=100),
            _line(2, "100", x=600, y=100),
            _line(3, "90", x=800, y=100),
            _line(4, "ngắn hạn", x=50, y=126),
            _line(5, "Nợ trung hạn", x=50, y=180),
        ],
        "page_sequence": 1,
    }

    result = build_accounting_family_topology_scan_v1([page], _generic_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    short = next(
        match for match in result["regions"][0]["child_matches"] if match["role"] == "SHORT_TERM"
    )
    assert short["surface"] == "Nợ ngắn hạn"
    assert short["source_line_indices"] == [1, 4]
    assert short["source_line_index"] == 1
    assert short["end_source_line_index"] == 4


def test_geometry_joins_wrapped_label_in_visual_not_provider_order() -> None:
    page = {
        "lines": [
            _line(0, "Phân tích dư nợ theo thời gian", y=20),
            _line(1, "hạn", x=50, y=152),
            _line(2, "Nợ ngắn", x=50, y=126),
            _line(3, "100", x=600, y=152),
            _line(4, "Nợ trung hạn", x=50, y=200),
        ],
        "page_sequence": 1,
    }

    result = build_accounting_family_topology_scan_v1([page], _generic_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    short = next(
        match for match in result["regions"][0]["child_matches"] if match["role"] == "SHORT_TERM"
    )
    assert short["surface"] == "Nợ ngắn hạn"
    assert "source_line_indices" not in short
    assert short["source_line_index"] == 1
    assert short["end_source_line_index"] == 2


def test_geometry_prefers_text_continuation_over_same_baseline_numeric_cell() -> None:
    spec = _generic_spec()
    spec["children"][0]["aliases"] = ["Nợ rất dài nhiều dòng ngắn hạn"]
    spec["limits"]["max_label_line_span"] = 6
    page = {
        "lines": [
            _line(0, "Phân tích dư nợ theo thời gian", y=20),
            _line(1, "Nợ rất", x=50, y=100),
            _line(2, "dài nhiều", x=50, y=126),
            _line(3, "dòng ngắn", x=50, y=152),
            _line(4, "100", x=430, y=176),
            _line(5, "hạn", x=50, y=178),
            _line(6, "Nợ trung hạn", x=50, y=220),
        ],
        "page_sequence": 1,
    }

    result = build_accounting_family_topology_scan_v1([page], spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    short = next(
        match for match in result["regions"][0]["child_matches"] if match["role"] == "SHORT_TERM"
    )
    assert short["surface"] == "Nợ rất dài nhiều dòng ngắn hạn"
    assert short["source_line_indices"] == [1, 2, 3, 5]


def test_role_occurrences_collapse_only_byte_identical_scan_candidates() -> None:
    spec = {
        "children": [
            {
                "aliases": ["Nợ đủ tiêu chuẩn"],
                "presence": "OPTIONAL",
                "role": "STANDARD",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Nợ cần chú ý"],
                "presence": "OPTIONAL",
                "role": "SPECIAL_MENTION",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Nợ dưới tiêu chuẩn"],
                "presence": "OPTIONAL",
                "role": "SUBSTANDARD",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "LOAN_QUALITY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 0,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Phân tích chất lượng nợ"],
            "resolution_mode": "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER",
            "role": "LOAN_QUALITY",
        },
        "presence_evidence_mode": "GLOBAL_CORE_HITS",
        "required_role_combinations": [
            ["STANDARD", "SPECIAL_MENTION"],
            ["STANDARD", "SUBSTANDARD"],
        ],
        "structural_reset_aliases": [],
    }
    page = _page(
        [
            "Nội dung dẫn nhập",
            "Nợ đủ tiêu chuẩn",
            "Nợ cần chú ý",
            "Nợ dưới tiêu chuẩn",
        ]
    )

    scan = build_accounting_family_topology_scan_v1([page], spec)

    assert len(scan["regions"]) == 2
    assert scan["regions"][0] == scan["regions"][1]
    occurrences = enumerate_accounting_family_role_occurrences_v1([page], spec, scan["regions"][0])
    assert [item["role"] for item in occurrences] == [
        "STANDARD",
        "SPECIAL_MENTION",
        "SUBSTANDARD",
    ]

    forged = copy.deepcopy(scan["regions"][0])
    forged["cluster_end_document_line_ordinal_exclusive"] -= 1
    with pytest.raises(AccountingFamilyTopologyV1Error):
        enumerate_accounting_family_role_occurrences_v1([page], spec, forged)


def _cash_spec() -> dict[str, object]:
    return json.loads(
        (_ROOT / "config/families/tm-cash-precious-metals-topology-v1.json").read_text(
            encoding="utf-8"
        )
    )


def _generic_spec(*, parent_mode: str = "EXPLICIT_ONLY") -> dict[str, object]:
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
            {
                "aliases": ["Nợ dài hạn"],
                "presence": "OPTIONAL",
                "role": "LONG_TERM",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "LOAN_MATURITY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": ["Phân tích chất lượng nợ"],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 3,
        },
        "parent": {
            "aliases": ["Phân tích dư nợ theo thời gian"],
            "resolution_mode": parent_mode,
            "role": "LOAN_MATURITY",
        },
        "structural_reset_aliases": ["Phân tích cho vay theo ngành"],
    }


def _parent_child_pair_spec(*, parent_mode: str = "EXPLICIT_ONLY") -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Nông nghiệp"],
                "presence": "REQUIRED",
                "role": "AGRICULTURE",
                "role_kind": "ADDITIVE_CHILD",
            }
        ],
        "family_id": "LOAN_INDUSTRY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V1",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Phân tích dư nợ theo ngành kinh tế"],
            "resolution_mode": parent_mode,
            "role": "LOAN_INDUSTRY",
        },
        "structural_reset_aliases": [],
    }


def _alternative_core_spec() -> dict[str, object]:
    return {
        "children": [
            {
                "aliases": ["Bằng VND"],
                "presence": "OPTIONAL",
                "role": "VND",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Bằng ngoại tệ"],
                "presence": "OPTIONAL",
                "role": "FOREIGN",
                "role_kind": "ADDITIVE_CHILD",
            },
            {
                "aliases": ["Tiền gửi tại NHNN Việt Nam"],
                "presence": "OPTIONAL",
                "role": "VIETNAM",
                "role_kind": "SOURCE_ONLY_GROUP_PARENT",
            },
            {
                "aliases": ["Tiền gửi tại Ngân hàng Nhà nước Lào"],
                "presence": "OPTIONAL",
                "role": "LAOS",
                "role_kind": "ADDITIVE_CHILD",
            },
        ],
        "family_id": "CENTRAL_BANK_DEPOSITS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V2",
        "hard_negative_aliases": [],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi tại NHNN"],
            "resolution_mode": "EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER",
            "role": "CENTRAL_BANK_DEPOSITS",
        },
        "presence_evidence_mode": "GLOBAL_CORE_HITS",
        "required_role_combinations": [["VND", "FOREIGN"], ["VIETNAM", "LAOS"]],
        "structural_reset_aliases": ["Tiền gửi và cho vay các TCTD khác"],
    }


def _contextual_interbank_spec() -> dict[str, object]:
    def group(role: str, aliases: list[str]) -> dict[str, object]:
        return {
            "matchers": [{"aliases": aliases, "within_role": None}],
            "presence": "OPTIONAL",
            "role": role,
            "role_kind": "STRUCTURAL_GROUP",
        }

    def currency(role: str, within_role: str, flattened: str) -> dict[str, object]:
        return {
            "matchers": [
                {"aliases": ["Bằng VND"], "within_role": within_role},
                {"aliases": [flattened], "within_role": None},
            ],
            "presence": "OPTIONAL",
            "role": role,
            "role_kind": "ADDITIVE_CHILD",
        }

    return {
        "children": [
            group(
                "DEMAND_GROUP",
                ["Tiền gửi không kỳ hạn", "Tiền gửi không kỳ hạn bằng VND"],
            ),
            currency(
                "DEMAND_VND",
                "DEMAND_GROUP",
                "Tiền gửi không kỳ hạn bằng VND",
            ),
            group("TERM_GROUP", ["Tiền gửi có kỳ hạn", "Tiền gửi có kỳ hạn bằng VND"]),
            currency("TERM_VND", "TERM_GROUP", "Tiền gửi có kỳ hạn bằng VND"),
            group("LOAN_GROUP", ["Cho vay các TCTD khác", "Cho vay bằng VND"]),
            currency("LOAN_VND", "LOAN_GROUP", "Cho vay bằng VND"),
        ],
        "family_id": "INTERBANK_DEPOSITS_AND_LOANS",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V3",
        "hard_negative_aliases": ["Tiền gửi và vay các TCTD khác"],
        "limits": {
            "max_cluster_span_lines": 30,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Tiền gửi và cho vay các TCTD khác"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "INTERBANK_DEPOSITS_AND_LOANS",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["DEMAND_GROUP", "TERM_GROUP", "LOAN_GROUP"]],
        "structural_reset_aliases": ["Chứng khoán kinh doanh"],
    }


def _flexible_role_pool_spec() -> dict[str, object]:
    def child(
        role: str, alias: str, *, within_role: str | None = None, kind: str = "ADDITIVE_CHILD"
    ) -> dict[str, object]:
        return {
            "matchers": [{"aliases": [alias], "within_role": within_role}],
            "presence": "OPTIONAL",
            "role": role,
            "role_kind": kind,
        }

    return {
        "children": [
            child("BRANCH", "Theo loại hình", kind="STRUCTURAL_GROUP"),
            child("ALPHA", "Loại A", within_role="BRANCH"),
            child("BETA", "Loại B"),
            child("GAMMA", "Loại C"),
        ],
        "family_id": "FLEXIBLE_SIBLING_FAMILY",
        "format_version": "ACCOUNTING_FAMILY_TOPOLOGY_SPEC_V4",
        "hard_negative_aliases": ["Bảng tiền gửi"],
        "limits": {
            "max_cluster_span_lines": 20,
            "max_continuation_pages": 1,
            "max_label_line_span": 2,
        },
        "parent": {
            "aliases": ["Bảng cho vay"],
            "resolution_mode": "EXPLICIT_ONLY",
            "role": "FLEXIBLE_SIBLING_FAMILY",
        },
        "presence_evidence_mode": "WITHIN_EXPLICIT_PARENT_CLUSTER",
        "required_role_combinations": [["BRANCH", "ALPHA"]],
        "required_role_pools": [{"minimum_count": 2, "roles": ["ALPHA", "BETA", "GAMMA"]}],
        "structural_reset_aliases": ["Bảng khác"],
    }


def test_v4_flexible_role_pool_accepts_exact_combination_or_two_distinct_siblings() -> None:
    spec = _flexible_role_pool_spec()
    contextual = build_accounting_family_topology_scan_v1(
        [_page(["Bảng cho vay", "Theo loại hình", "Loại A"])], spec
    )
    branchless = build_accounting_family_topology_scan_v1(
        [_page(["Bảng cho vay", "Loại C", "Loại B"])], spec
    )

    assert contextual["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert contextual["regions"][0]["observed_roles"] == ["BRANCH", "ALPHA"]
    assert contextual["regions"][0]["child_matches"][1]["matched_within_role"] == "BRANCH"
    assert branchless["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert branchless["regions"][0]["observed_roles"] == ["GAMMA", "BETA"]


def test_v4_weak_context_free_matcher_needs_one_independent_presence_anchor() -> None:
    spec = _flexible_role_pool_spec()
    beta = next(child for child in spec["children"] if child["role"] == "BETA")
    beta["matchers"][0]["presence_anchor"] = False

    weak_only = build_accounting_family_topology_scan_v1([_page(["Bảng cho vay", "Loại B"])], spec)
    completed = build_accounting_family_topology_scan_v1(
        [_page(["Bảng cho vay", "Loại B", "Loại C"])], spec
    )

    assert weak_only["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert weak_only["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert weak_only["near_regions"][0]["observed_roles"] == ["BETA"]
    assert completed["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert completed["regions"][0]["observed_roles"] == ["BETA", "GAMMA"]
    assert completed["metrics"]["core_semantic_anchor_hit_count"] == 1

    invalid = copy.deepcopy(spec)
    invalid_beta = next(child for child in invalid["children"] if child["role"] == "BETA")
    invalid_beta["matchers"][0]["presence_anchor"] = "false"
    with pytest.raises(AccountingFamilyTopologyV1Error, match="matcher fields drifted"):
        build_accounting_family_topology_scan_v1([_page(["Bảng cho vay"])], invalid)


def test_v4_flexible_role_pool_counts_distinct_roles_and_fills_continuation_deficit() -> None:
    spec = _flexible_role_pool_spec()
    repeated_one_role = build_accounting_family_topology_scan_v1(
        [_page(["Bảng cho vay", "Loại B", "Loại B"])], spec
    )
    continued = build_accounting_family_topology_scan_v1(
        [
            _page(["Bảng cho vay", "Loại B"], page_sequence=1),
            _page(["Loại C"], page_sequence=2),
        ],
        spec,
    )

    assert repeated_one_role["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert repeated_one_role["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_ROLE_COMBINATION:BRANCH+ALPHA",
        "MISSING_REQUIRED_ROLE_POOL:MINIMUM_2:ALPHA+BETA+GAMMA",
    ]
    assert continued["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert continued["regions"][0]["continuation_page_count"] == 1
    assert continued["metrics"]["core_semantic_anchor_hit_count"] == 2


def test_v4_flexible_role_pool_spec_rejects_field_and_semantic_drift() -> None:
    missing = _flexible_role_pool_spec()
    missing.pop("required_role_pools")
    with pytest.raises(AccountingFamilyTopologyV1Error):
        build_accounting_family_topology_scan_v1([_page(["Bảng cho vay"])], missing)

    duplicate = _flexible_role_pool_spec()
    duplicate["required_role_pools"].append(
        {"minimum_count": 2, "roles": ["GAMMA", "BETA", "ALPHA"]}
    )
    with pytest.raises(AccountingFamilyTopologyV1Error):
        build_accounting_family_topology_scan_v1([_page(["Bảng cho vay"])], duplicate)

    partial_minimum = _flexible_role_pool_spec()
    partial_minimum["required_role_pools"][0]["minimum_count"] = 1
    with pytest.raises(AccountingFamilyTopologyV1Error):
        build_accounting_family_topology_scan_v1([_page(["Bảng cho vay"])], partial_minimum)


def test_wrapped_label_span_policy_is_bounded_at_six_lines() -> None:
    admitted = _generic_spec()
    admitted["limits"]["max_label_line_span"] = 6
    rejected = copy.deepcopy(admitted)
    rejected["limits"]["max_label_line_span"] = 7

    assert (
        build_accounting_family_topology_scan_v1(
            [_page(["Phân tích dư nợ theo thời gian", "Nợ ngắn hạn", "Nợ trung hạn"])],
            admitted,
        )["status"]
        == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    )
    with pytest.raises(AccountingFamilyTopologyV1Error, match="maximum label line span"):
        build_accounting_family_topology_scan_v1([_page(["Nợ ngắn hạn"])], rejected)


def test_cash_spec_is_declarative_and_accepts_reordered_wrapped_children() -> None:
    pages = [
        _page(
            [
                "Tiền mặt, vàng bạc, đá quý",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Tiền mặt bằng ngoại tệ",
                "20",
                "21",
                "Tiền mặt bằng Đồng",
                "Việt Nam",
                "10",
                "11",
                "Vàng",
                "1",
                "2",
                "31",
                "34",
                "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                "31/12/2026",
                "31/12/2025",
            ]
        )
    ]

    result = build_accounting_family_topology_scan_v1(pages, _cash_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["metrics"] == {
        "complete_region_count": 1,
        "core_semantic_anchor_hit_count": 2,
        "explicit_parent_region_count": 1,
        "implied_parent_region_count": 0,
        "near_region_count": 0,
        "reordered_complete_region_count": 1,
        "semantic_anchor_hit_count": 4,
    }
    region = result["regions"][0]
    assert region["cluster_end_source_line_index_exclusive"] == 16
    assert region["observed_roles"] == ["CASH_FOREIGN", "CASH_VND", "MONETARY_GOLD"]
    assert region["preferred_sibling_order_preserved"] is False
    assert region["child_matches"][1]["surface"] == "Tiền mặt bằng Đồng Việt Nam"
    assert region["minimal_unique_anchor"]["combination_size"] == 2
    assert result["safety"]["bank_filename_note_page_year_used_for_matching"] is False


def test_empty_semantic_neighbor_never_expands_an_exact_label_span() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Phân tích dư nợ theo thời gian",
                    "",
                    "Nợ ngắn hạn",
                    "Nợ trung hạn",
                ]
            )
        ],
        _generic_spec(),
    )

    region = result["regions"][0]
    short = next(match for match in region["child_matches"] if match["role"] == "SHORT_TERM")
    assert short["source_line_index"] == short["end_source_line_index"] == 2


@pytest.mark.parametrize("parent", ["Tiền mặt và vàng", "Tiền mặt và vàng bạc"])
def test_cash_spec_accepts_conjunction_parent_variant_without_routing(parent: str) -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    f"4. {parent}",
                    "Tiền mặt bằng VND",
                    "100",
                    "Tiền mặt bằng ngoại tệ",
                    "20",
                    "Vàng tiền tệ",
                    "1",
                    "121",
                ]
            )
        ],
        _cash_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["parent_resolution"] == "EXPLICIT_PARENT"
    assert region["parent_match"]["surface"] == f"4. {parent}"


def test_cash_spec_uses_bounded_one_edit_rescue_for_observed_ocr_errors() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "4. Tiền mặt và vàng",
                    "Tiện mặt bằng VND",
                    "100",
                    "Tiền mặt bảng ngoại tệ",
                    "20",
                    "Vùng tiền tệ",
                    "1",
                    "121",
                ]
            )
        ],
        _cash_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = {item["role"]: item for item in result["regions"][0]["child_matches"]}
    assert {role: (item["surface"], item["match_kind"]) for role, item in matches.items()} == {
        "CASH_VND": ("Tiện mặt bằng VND", "EXACT_ACCENTLESS_ALIAS"),
        "CASH_FOREIGN": (
            "Tiền mặt bảng ngoại tệ",
            "EXACT_ACCENTLESS_ALIAS",
        ),
        "MONETARY_GOLD": (
            "Vùng tiền tệ",
            "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY",
        ),
    }


def test_parent_can_be_implied_only_when_the_declarative_family_permits_it() -> None:
    pages = [_page(["Nợ trung hạn", "2", "Nợ ngắn hạn", "1", "Nợ dài hạn", "3"])]

    explicit_only = build_accounting_family_topology_scan_v1(pages, _generic_spec())
    implied = build_accounting_family_topology_scan_v1(
        pages,
        _generic_spec(parent_mode="EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"),
    )

    assert explicit_only["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert implied["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert implied["regions"][0]["parent_resolution"] == "IMPLIED_BY_REQUIRED_CHILD_CLUSTER"
    assert implied["regions"][0]["preferred_sibling_order_preserved"] is False


@pytest.mark.parametrize(
    "rows",
    [
        ["Tiền gửi tại NHNN", "Bằng VND", "100", "Bằng ngoại tệ", "20", "120"],
        [
            "Tiền gửi tại NHNN",
            "Tiền gửi tại NHNN Việt Nam",
            "100",
            "Tiền gửi tại Ngân hàng Nhà nước Lào",
            "20",
            "120",
        ],
    ],
)
def test_alternative_core_role_combinations_accept_distinct_generic_variants(
    rows: list[str],
) -> None:
    result = build_accounting_family_topology_scan_v1([_page(rows)], _alternative_core_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "minimal_role_combination_proved": True,
    }


def test_alternative_core_explicit_parent_plus_one_child_is_a_bounded_pair() -> None:
    spec = _alternative_core_spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_ONLY"
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"
    spec["required_role_combinations"] = [["VIETNAM"]]

    result = build_accounting_family_topology_scan_v1(
        [_page(["Tiền gửi tại NHNN", "Tiền gửi tại NHNN Việt Nam", "100"])],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["minimal_unique_anchor"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "selected_roles": ["PARENT:CENTRAL_BANK_DEPOSITS", "CHILD:VIETNAM"],
    }


def test_alternative_core_one_child_never_enables_parentless_inference() -> None:
    spec = _alternative_core_spec()
    spec["required_role_combinations"] = [["VIETNAM"]]

    with pytest.raises(AccountingFamilyTopologyV1Error, match="explicit parent-scoped"):
        build_accounting_family_topology_scan_v1(
            [_page(["Tiền gửi tại NHNN Việt Nam", "100"])],
            spec,
        )


def test_contextual_roles_disambiguate_repeated_currency_labels_by_structural_parent() -> None:
    spec = _contextual_interbank_spec()
    for child in spec["children"]:
        if child["role"].endswith("_VND"):
            child["matchers"] = child["matchers"][:1]
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn",
                    "Bằng VND",
                    "100",
                    "Tiền gửi có kỳ hạn",
                    "Bằng VND",
                    "200",
                    "Cho vay các TCTD khác",
                    "Bằng VND",
                    "50",
                    "350",
                    "Chứng khoán kinh doanh",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = {item["role"]: item for item in result["regions"][0]["child_matches"]}
    assert matches["DEMAND_VND"]["source_line_index"] == 2
    assert matches["DEMAND_VND"]["matched_within_role"] == "DEMAND_GROUP"
    assert matches["TERM_VND"]["source_line_index"] == 5
    assert matches["TERM_VND"]["matched_within_role"] == "TERM_GROUP"
    assert matches["LOAN_VND"]["source_line_index"] == 8
    assert matches["LOAN_VND"]["matched_within_role"] == "LOAN_GROUP"


def test_contextual_roles_accept_flattened_rows_without_bank_or_layout_routing() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn bằng VND",
                    "100",
                    "Tiền gửi có kỳ hạn bằng VND",
                    "200",
                    "Cho vay bằng VND",
                    "50",
                    "350",
                    "Chứng khoán kinh doanh",
                ]
            )
        ],
        _contextual_interbank_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = {item["role"]: item for item in result["regions"][0]["child_matches"]}
    assert matches["DEMAND_VND"]["matched_within_role"] is None
    assert matches["TERM_VND"]["matched_within_role"] is None
    assert matches["LOAN_VND"]["matched_within_role"] is None


def test_contextual_v3_ignores_bounded_footnotes_and_uppercase_acronyms() -> None:
    spec = _contextual_interbank_spec()
    spec["parent"]["aliases"].append("Tiền gửi và cho vay các tổ chức tín dụng khác")
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    'Tiền gửi và cho vay các tổ chức tín dụng ("TCTD") khác',
                    "Tiền gửi không kỳ hạn",
                    "Bằng VND",
                    "100",
                    "Tiền gửi có kỳ hạn (i)",
                    "Bằng VND",
                    "200",
                    "Cho vay các TCTD khác (1)",
                    "Bằng VND",
                    "50",
                    "350",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["parent_match"]["match_kind"] == (
        "EXACT_ACCENTLESS_ALIAS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
    )
    matches = {item["role"]: item for item in region["child_matches"]}
    assert matches["TERM_GROUP"]["match_kind"] == (
        "EXACT_ACCENTLESS_ALIAS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
    )
    assert matches["LOAN_GROUP"]["match_kind"] == (
        "EXACT_ACCENTLESS_ALIAS_AFTER_DECORATIVE_PARENTHETICAL_REMOVAL"
    )


def test_contextual_v3_does_not_strip_semantic_parenthetical_qualifiers() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn",
                    "Bằng VND",
                    "100",
                    "Tiền gửi có kỳ hạn (không bao gồm tiền gửi ký quỹ)",
                    "Bằng VND",
                    "200",
                    "Cho vay các TCTD khác",
                    "Bằng VND",
                    "50",
                ]
            )
        ],
        _contextual_interbank_spec(),
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_ROLE_COMBINATION:DEMAND_GROUP+TERM_GROUP+LOAN_GROUP"
    ]


def test_contextual_v3_joins_repeated_continuation_and_prefers_richer_note() -> None:
    spec = _contextual_interbank_spec()
    spec["required_role_combinations"].append(["DEMAND_GROUP", "LOAN_GROUP"])
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn",
                    "100",
                    "Cho vay các TCTD khác",
                    "50",
                ],
                page_sequence=1,
            ),
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác",
                    "Tiền gửi không kỳ hạn",
                    "Bằng VND",
                    "100",
                    "Tiền gửi có kỳ hạn",
                    "Bằng VND",
                    "200",
                ],
                page_sequence=2,
            ),
            _page(
                [
                    "Tiền gửi và cho vay các TCTD khác (TIẾP THEO)",
                    "Cho vay các TCTD khác",
                    "Bằng VND",
                    "50",
                    "350",
                    "Chứng khoán kinh doanh",
                ],
                page_sequence=3,
            ),
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["page_sequence"] == 2
    assert region["continuation_page_count"] == 1
    assert region["observed_roles"] == [
        "DEMAND_GROUP",
        "DEMAND_VND",
        "TERM_GROUP",
        "TERM_VND",
        "LOAN_GROUP",
        "LOAN_VND",
    ]


def test_contextual_role_cannot_borrow_same_currency_label_from_sibling_group() -> None:
    spec = _contextual_interbank_spec()
    pages = [
        _page(
            [
                "Tiền gửi và cho vay các TCTD khác",
                "Tiền gửi không kỳ hạn",
                "Bằng VND",
                "100",
                "Tiền gửi có kỳ hạn",
                "200",
                "Cho vay các TCTD khác",
                "Bằng VND",
                "50",
                "350",
            ]
        )
    ]

    result = build_accounting_family_topology_scan_v1(pages, spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    roles = {item["role"] for item in result["regions"][0]["child_matches"]}
    assert "DEMAND_VND" in roles
    assert "TERM_VND" not in roles
    assert "LOAN_VND" in roles


def test_contextual_role_uses_visual_order_when_provider_order_is_reversed() -> None:
    spec = _contextual_interbank_spec()
    for child in spec["children"]:
        if child["role"].endswith("_VND"):
            child["matchers"] = child["matchers"][:1]
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", y=0),
        # The provider emitted the visually later child before its group.
        _line(1, "Bằng VND", y=150),
        _line(2, "Tiền gửi không kỳ hạn", y=90),
        _line(3, "Tiền gửi có kỳ hạn", y=210),
        _line(4, "Bằng VND", y=240),
        _line(5, "Cho vay các TCTD khác", y=300),
        _line(6, "Bằng VND", y=330),
    ]

    result = build_accounting_family_topology_scan_v1([{"lines": lines, "page_sequence": 1}], spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = {item["role"]: item for item in result["regions"][0]["child_matches"]}
    assert matches["DEMAND_VND"]["source_line_index"] == 1
    assert matches["DEMAND_VND"]["matched_within_role"] == "DEMAND_GROUP"
    assert matches["TERM_VND"]["source_line_index"] == 4
    assert matches["LOAN_VND"]["source_line_index"] == 6


def test_contextual_twin_wins_over_context_free_twin_after_provider_reorder() -> None:
    spec = _contextual_interbank_spec()
    # Both matchers intentionally recognize the same surface.  Visual order,
    # rather than the provider's reversed source order, binds it to the group.
    spec["children"][1]["matchers"][1]["aliases"] = ["Bằng VND"]
    lines = [
        _line(0, "Tiền gửi và cho vay các TCTD khác", y=0),
        _line(1, "Bằng VND", y=150),
        _line(2, "Tiền gửi không kỳ hạn", y=90),
        _line(3, "Tiền gửi có kỳ hạn", y=210),
        _line(4, "Bằng VND", y=240),
        _line(5, "Cho vay các TCTD khác", y=300),
        _line(6, "Bằng VND", y=330),
    ]

    result = build_accounting_family_topology_scan_v1([{"lines": lines, "page_sequence": 1}], spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    matches = {item["role"]: item for item in result["regions"][0]["child_matches"]}
    assert matches["DEMAND_VND"]["source_line_index"] == 1
    assert matches["DEMAND_VND"]["matched_within_role"] == "DEMAND_GROUP"


def test_contextual_spec_rejects_unknown_nonstructural_or_cyclic_contexts() -> None:
    unknown = _contextual_interbank_spec()
    unknown["children"][1]["matchers"][0]["within_role"] = "UNKNOWN"
    with pytest.raises(AccountingFamilyTopologyV1Error, match="structural role"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], unknown)

    nonstructural = _contextual_interbank_spec()
    nonstructural["children"][1]["matchers"][0]["within_role"] = "TERM_VND"
    with pytest.raises(AccountingFamilyTopologyV1Error, match="structural role"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], nonstructural)

    cyclic = _contextual_interbank_spec()
    cyclic["children"][0]["matchers"][0]["within_role"] = "TERM_GROUP"
    cyclic["children"][2]["matchers"][0]["within_role"] = "DEMAND_GROUP"
    with pytest.raises(AccountingFamilyTopologyV1Error, match="cycle"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], cyclic)


def test_alternative_core_parent_only_is_not_observed_but_partial_core_is_unresolved() -> None:
    parent_only = build_accounting_family_topology_scan_v1(
        [_page(["Tiền gửi tại NHNN", "100", "90"])], _alternative_core_spec()
    )
    partial = build_accounting_family_topology_scan_v1(
        [_page(["Tiền gửi tại NHNN", "Tiền gửi tại NHNN Việt Nam", "100"])],
        _alternative_core_spec(),
    )

    assert parent_only["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert parent_only["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert partial["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert partial["metrics"]["core_semantic_anchor_hit_count"] == 1
    assert partial["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_ROLE_COMBINATION:VND+FOREIGN|VIETNAM+LAOS"
    ]


def test_alternative_core_rejects_required_presence_and_unknown_combination_role() -> None:
    required = _alternative_core_spec()
    required["children"][0]["presence"] = "REQUIRED"
    with pytest.raises(AccountingFamilyTopologyV1Error, match="must use OPTIONAL"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], required)

    unknown = _alternative_core_spec()
    unknown["required_role_combinations"] = [["VND", "UNKNOWN"]]
    with pytest.raises(AccountingFamilyTopologyV1Error, match="combination"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], unknown)


def test_explicit_cluster_presence_mode_ignores_generic_child_pairs_outside_parent() -> None:
    spec = _alternative_core_spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_ONLY"
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"
    absent_detail = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi tại NHNN",
                    "100",
                    "Tiền gửi và cho vay các TCTD khác",
                    "Bằng VND",
                    "80",
                    "Bằng ngoại tệ",
                    "20",
                ]
            )
        ],
        spec,
    )
    partial_detail = build_accounting_family_topology_scan_v1(
        [_page(["Tiền gửi tại NHNN", "Bằng VND", "100"])],
        spec,
    )

    assert absent_detail["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert absent_detail["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert partial_detail["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert partial_detail["metrics"]["core_semantic_anchor_hit_count"] == 1


def test_explicit_cluster_presence_mode_requires_explicit_only_parent_resolution() -> None:
    spec = _alternative_core_spec()
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"

    with pytest.raises(AccountingFamilyTopologyV1Error, match="presence evidence mode"):
        build_accounting_family_topology_scan_v1([_page(["Bằng VND"])], spec)


def test_source_only_group_parent_can_share_the_explicit_family_parent_row() -> None:
    spec = _alternative_core_spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_ONLY"
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"
    spec["children"][2]["aliases"].append("Tiền gửi tại NHNN")

    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi tại NHNN",
                    "100",
                    "90",
                    "Tiền gửi tại Ngân hàng Nhà nước Lào",
                    "20",
                    "10",
                    "120",
                    "100",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["observed_roles"] == ["VIETNAM", "LAOS"]
    assert region["parent_match"]["document_line_ordinal"] == 0
    assert region["child_matches"][0]["document_line_ordinal"] == 0


def test_coextensive_source_group_is_not_duplicated_when_another_core_is_complete() -> None:
    spec = _alternative_core_spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_ONLY"
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"
    spec["children"][2]["aliases"].append("Tiền gửi tại NHNN")

    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi tại NHNN",
                    "31/12/2025",
                    "31/12/2024",
                    "Bằng VND",
                    "100",
                    "90",
                    "Bằng ngoại tệ",
                    "20",
                    "10",
                    "120",
                    "100",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["observed_roles"] == ["VND", "FOREIGN"]


def test_nested_source_group_parent_does_not_hide_outer_family_header() -> None:
    spec = _alternative_core_spec()
    spec["parent"]["resolution_mode"] = "EXPLICIT_ONLY"
    spec["presence_evidence_mode"] = "WITHIN_EXPLICIT_PARENT_CLUSTER"
    spec["parent"]["aliases"].append("Tiền gửi tại NHNN Việt Nam")

    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền gửi tại NHNN",
                    "31/12/2025",
                    "31/12/2024",
                    "Triệu đồng",
                    "Tiền gửi tại NHNN Việt Nam",
                    "100",
                    "90",
                    "Bằng VND",
                    "80",
                    "70",
                    "Bằng ngoại tệ",
                    "20",
                    "20",
                    "Tiền gửi tại Ngân hàng Nhà nước Lào",
                    "10",
                    "5",
                    "110",
                    "95",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["metrics"]["complete_region_count"] == 1
    region = result["regions"][0]
    assert region["parent_match"]["document_line_ordinal"] == 0
    assert region["cluster_start_source_line_index"] == 0
    assert (
        next(item for item in region["child_matches"] if item["role"] == "VIETNAM")[
            "document_line_ordinal"
        ]
        == 4
    )


@pytest.mark.parametrize(
    "surface",
    [
        "1. Phân tích dư nợ theo thời gian",
        "(1) Phân tích dư nợ theo thời gian",
        "II- Phân tích dư nợ theo thời gian",
        "a) Phân tích dư nợ theo thời gian",
    ],
)
def test_generic_enumeration_prefix_does_not_hide_explicit_parent(surface: str) -> None:
    result = build_accounting_family_topology_scan_v1(
        [_page([surface, "Nợ ngắn hạn", "100", "Nợ trung hạn", "200"])],
        _generic_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    parent = result["regions"][0]["parent_match"]
    assert parent["surface"] == surface
    assert "AFTER_ENUMERATION_PREFIX" in parent["match_kind"]


def test_plain_leading_number_without_enumeration_punctuation_is_not_stripped() -> None:
    result = build_accounting_family_topology_scan_v1(
        [_page(["1 Phân tích dư nợ theo thời gian", "Nợ ngắn hạn", "100", "Nợ trung hạn", "200"])],
        _generic_spec(),
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_long_label_one_edit_rescue_remains_available_inside_complete_topology() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Phân tích dư nợ theo thời gian",
                    "Nợ ngắn hạn",
                    "100",
                    "Nợ trung hạna",
                    "200",
                ]
            )
        ],
        _generic_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    medium = next(
        item for item in result["regions"][0]["child_matches"] if item["role"] == "MEDIUM_TERM"
    )
    assert medium["match_kind"] == "ONE_EDIT_ALIAS_REQUIRES_COMPLETE_TOPOLOGY"


def test_short_generic_one_edit_alias_cannot_invent_an_optional_child() -> None:
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "Tiền mặt, vàng bạc, đá quý",
                    "Tiền mặt bằng VND",
                    "100",
                    "Tiền mặt bằng ngoại tệ",
                    "20",
                    "hàng",
                    "1",
                    "120",
                ]
            )
        ],
        _cash_spec(),
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["observed_roles"] == ["CASH_VND", "CASH_FOREIGN"]


def test_complete_document_without_any_family_anchor_is_distinct_from_partial_match() -> None:
    absent = build_accounting_family_topology_scan_v1(
        [_page(["Chứng khoán kinh doanh", "100", "200"])],
        _generic_spec(),
    )
    partial = build_accounting_family_topology_scan_v1(
        [_page(["Nợ ngắn hạn", "100"])],
        _generic_spec(),
    )

    assert absent["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert absent["metrics"]["semantic_anchor_hit_count"] == 0
    assert absent["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert absent["regions"] == []
    assert absent["near_regions"] == []
    assert partial["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert partial["metrics"]["semantic_anchor_hit_count"] == 1
    assert partial["metrics"]["core_semantic_anchor_hit_count"] == 1


def test_optional_child_surface_alone_does_not_claim_partial_family_presence() -> None:
    result = build_accounting_family_topology_scan_v1(
        [_page(["Nợ dài hạn", "100"])],
        _generic_spec(),
    )

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["metrics"]["semantic_anchor_hit_count"] == 1
    assert result["metrics"]["core_semantic_anchor_hit_count"] == 0


def test_parent_summary_without_any_required_child_is_not_a_detailed_family_region() -> None:
    result = build_accounting_family_topology_scan_v1(
        [_page(["Phân tích dư nợ theo thời gian", "1.000", "2.000"])],
        _generic_spec(),
    )

    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["metrics"]["semantic_anchor_hit_count"] == 1
    assert result["metrics"]["core_semantic_anchor_hit_count"] == 0
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_CHILD:MEDIUM_TERM",
        "MISSING_REQUIRED_CHILD:SHORT_TERM",
    ]


def test_explicit_parent_plus_one_required_child_can_prove_unique_pair() -> None:
    pages = [_page(["Phân tích dư nợ theo ngành kinh tế", "Nông nghiệp", "100"])]

    explicit = build_accounting_family_topology_scan_v1(pages, _parent_child_pair_spec())
    missing_parent = build_accounting_family_topology_scan_v1(
        [_page(["Nông nghiệp", "100"])],
        _parent_child_pair_spec(parent_mode="EXPLICIT_OR_UNIQUE_REQUIRED_CHILD_CLUSTER"),
    )

    assert explicit["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert explicit["regions"][0]["minimal_unique_anchor"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "selected_roles": ["PARENT:LOAN_INDUSTRY", "CHILD:AGRICULTURE"],
    }
    assert missing_parent["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_explicit_family_can_continue_once_across_a_physical_page_boundary() -> None:
    pages = [
        _page(
            [
                "Phân tích dư nợ theo thời gian",
                "Nợ ngắn hạn",
                "100",
            ],
            page_sequence=1,
        ),
        _page(
            [
                "Nợ trung hạn",
                "200",
                "Nợ dài hạn",
                "300",
            ],
            page_sequence=2,
        ),
    ]

    result = build_accounting_family_topology_scan_v1(pages, _generic_spec())

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["continuation_page_count"] == 1
    assert region["page_sequence"] == 1
    assert region["cluster_end_page_sequence_inclusive"] == 2
    assert region["cluster_end_source_line_index_exclusive"] is None
    assert [item["page_sequence"] for item in region["child_matches"]] == [1, 2, 2]
    assert region["minimal_unique_anchor"]["combination_size"] == 2


def test_next_page_must_fill_a_role_deficit_not_only_expose_a_generic_total() -> None:
    spec = _generic_spec()
    spec["children"].append(
        {
            "aliases": ["Giá trị thuần"],
            "presence": "OPTIONAL",
            "role": "GENERIC_NET_TOTAL",
            "role_kind": "TOTAL",
        }
    )
    pages = [
        _page(
            [
                "Phân tích dư nợ theo thời gian",
                "Nợ ngắn hạn",
                "100",
                "Nợ trung hạn",
                "200",
            ],
            page_sequence=1,
        ),
        _page(
            [
                "Công cụ tài chính phái sinh",
                "Giá trị thuần",
                "999",
            ],
            page_sequence=2,
        ),
    ]

    result = build_accounting_family_topology_scan_v1(pages, spec)

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["continuation_page_count"] == 0
    assert region["observed_roles"] == ["SHORT_TERM", "MEDIUM_TERM"]
    assert region["cluster_end_source_line_index_exclusive"] is None


def test_trading_region_stops_before_derivative_heading_with_asset_liability_qualifier() -> None:
    spec = json.loads(
        (_ROOT / "config/families/tm-trading-securities-topology-v1.json").read_text(
            encoding="utf-8"
        )
    )
    result = build_accounting_family_topology_scan_v1(
        [
            _page(
                [
                    "1. CHỨNG KHOÁN KINH DOANH",
                    "Chứng khoán nợ",
                    "100",
                    "Chứng khoán vốn",
                    "200",
                    "2 CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(CÔNG NỢ) TÀI CHÍNH KHÁC",
                    "Giá trị thuần",
                    "999",
                ]
            )
        ],
        spec,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    region = result["regions"][0]
    assert region["cluster_end_source_line_index_exclusive"] == 5
    assert [item["role"] for item in region["child_matches"]] == [
        "DEBT_SECURITIES_GROUP",
        "EQUITY_SECURITIES_GROUP",
    ]


def test_continuation_budget_and_next_page_reset_both_fail_closed() -> None:
    pages = [
        _page(
            ["Phân tích dư nợ theo thời gian", "Nợ ngắn hạn", "100"],
            page_sequence=1,
        ),
        _page(["Nợ trung hạn", "200"], page_sequence=2),
    ]
    no_continuation = _generic_spec()
    no_continuation["limits"]["max_continuation_pages"] = 0

    bounded = build_accounting_family_topology_scan_v1(pages, no_continuation)
    reset = build_accounting_family_topology_scan_v1(
        [
            pages[0],
            _page(
                ["Phân tích cho vay theo ngành kinh tế", "Nợ trung hạn", "200"],
                page_sequence=2,
            ),
        ],
        _generic_spec(),
    )

    assert bounded["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert bounded["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_CHILD:MEDIUM_TERM"
    ]
    assert reset["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert reset["near_regions"][0]["unresolved_reasons"] == ["MISSING_REQUIRED_CHILD:MEDIUM_TERM"]


def test_hard_negative_and_structural_reset_fail_closed_without_layout_routing() -> None:
    hard_negative = _page(
        [
            "Phân tích dư nợ theo thời gian",
            "Phân tích chất lượng nợ",
            "Nợ ngắn hạn",
            "1",
            "Nợ trung hạn",
            "2",
        ]
    )
    reset = _page(
        [
            "Phân tích dư nợ theo thời gian",
            "Nợ ngắn hạn",
            "1",
            "Phân tích cho vay theo ngành",
            "Nợ trung hạn",
            "2",
        ]
    )

    negative_result = build_accounting_family_topology_scan_v1([hard_negative], _generic_spec())
    reset_result = build_accounting_family_topology_scan_v1([reset], _generic_spec())

    assert negative_result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert negative_result["near_regions"][0]["unresolved_reasons"] == [
        "HARD_NEGATIVE_FAMILY_IN_CLUSTER"
    ]
    assert reset_result["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_REQUIRED_CHILD:MEDIUM_TERM"
    ]


def test_multiple_complete_regions_do_not_claim_document_uniqueness() -> None:
    surfaces = [
        "Phân tích dư nợ theo thời gian",
        "Nợ ngắn hạn",
        "1",
        "Nợ trung hạn",
        "2",
        "Phân tích cho vay theo ngành",
        "Phân tích dư nợ theo thời gian",
        "Nợ ngắn hạn",
        "3",
        "Nợ trung hạn",
        "4",
    ]

    result = build_accounting_family_topology_scan_v1([_page(surfaces)], _generic_spec())

    assert result["status"] == "UNRESOLVED_MULTIPLE_OR_NONUNIQUE_COMPLETE_REGIONS"
    assert result["metrics"]["complete_region_count"] == 2
    assert result["uniqueness"]["minimal_role_combination_proved"] is False
    assert all(region["minimal_unique_anchor"] is None for region in result["regions"])


def test_exact_replay_rejects_coordinated_result_rehash_and_spec_bank_field() -> None:
    pages = [
        _page(
            [
                "Phân tích dư nợ theo thời gian",
                "Nợ ngắn hạn",
                "1",
                "Nợ trung hạn",
                "2",
            ]
        )
    ]
    spec = _generic_spec()
    result = build_accounting_family_topology_scan_v1(pages, spec)
    forged = copy.deepcopy(result)
    forged["regions"][0]["observed_roles"] = ["SHORT_TERM", "LONG_TERM"]
    material = copy.deepcopy(forged)
    material.pop("scan_id")
    forged["scan_id"] = "aftv1:scan:" + canonical_json_sha256_v1(material)

    with pytest.raises(AccountingFamilyTopologyV1Error, match="replay exactly"):
        validate_accounting_family_topology_scan_replay_v1(forged, pages, spec)
    with pytest.raises(AccountingFamilyTopologyV1Error, match="spec fields"):
        build_accounting_family_topology_scan_v1(pages, spec | {"bank": "MBB"})
