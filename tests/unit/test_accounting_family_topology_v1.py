from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.accounting_family_topology_v1 import (
    AccountingFamilyTopologyV1Error,
    build_accounting_family_topology_scan_v1,
    validate_accounting_family_topology_scan_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]


def _line(index: int, text: str, *, x: int = 20, y: int | None = None) -> dict[str, object]:
    top = index * 30 if y is None else y
    return {
        "bbox": [x, top, x + 360, top + 22],
        "source_line_index": index,
        "source_text": None,
        "vietocr_text": text,
    }


def _page(surfaces: list[str], page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [_line(index, text) for index, text in enumerate(surfaces)],
        "page_sequence": page_sequence,
    }


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
                ["Phân tích cho vay theo ngành", "Nợ trung hạn", "200"],
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
