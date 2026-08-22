from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.evaluation import accounting_family_topology_v1 as topology_v1

_ROOT = Path(__file__).resolve().parents[2]
_CONFIG = _ROOT / "config/families/tm-derivative-financial-instruments-topology-v1.json"


def _spec() -> dict[str, object]:
    return json.loads(_CONFIG.read_text(encoding="utf-8"))


def _page(*labels: str) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [30, 30 + ordinal * 35, 900, 60 + ordinal * 35],
                "source_line_index": ordinal,
                "source_text": None,
                "vietocr_text": label,
            }
            for ordinal, label in enumerate(labels)
        ],
        "page_sequence": 1,
    }


def test_config_is_bank_period_page_and_schema_blind() -> None:
    spec = _spec()
    compiled = topology_v1._spec(spec)
    assert compiled["family_id"] == "DERIVATIVE_FINANCIAL_INSTRUMENTS"
    serialized = json.dumps(spec, ensure_ascii=False).casefold()
    for forbidden in (
        "acb",
        "mbb",
        "vpb",
        "hdb",
        "vcb",
        "ctg",
        "bid",
        "vib",
        "2025",
        "2026",
        "physical_page",
        "reportnormid",
    ):
        assert forbidden not in serialized


def test_grouped_and_direct_child_presentations_share_one_spec() -> None:
    grouped = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN/(CÔNG NỢ) TÀI CHÍNH KHÁC",
                "Công cụ tài chính phái sinh tiền tệ",
                "Giao dịch kỳ hạn tiền tệ",
                "Giao dịch hoán đổi tiền tệ",
                "Công cụ tài chính phái sinh khác",
                "Giao dịch hoán đổi lãi suất",
                "Cho vay khách hàng",
            )
        ],
        _spec(),
    )
    direct = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ TÀI CHÍNH KHÁC",
                "Tại ngày cuối kỳ",
                "Giao dịch kỳ hạn tiền tệ",
                "Giao dịch hoán đổi tiền tệ",
                "Giao dịch hoán đổi lãi suất",
                "Tại ngày đầu kỳ",
                "Giao dịch kỳ hạn tiền tệ",
                "Giao dịch hoán đổi tiền tệ",
                "Giao dịch hoán đổi lãi suất",
            )
        ],
        _spec(),
    )
    assert grouped["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert direct["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert grouped["regions"][0]["parent_resolution"] == "EXPLICIT_PARENT"
    assert set(grouped["regions"][0]["observed_roles"]) == {
        "CURRENCY_DERIVATIVE_GROUP",
        "FORWARD_CURRENCY",
        "CURRENCY_SWAP",
        "OTHER_DERIVATIVE_GROUP",
        "INTEREST_RATE_SWAP",
    }
    assert set(direct["regions"][0]["observed_roles"]) == {
        "FORWARD_CURRENCY",
        "CURRENCY_SWAP",
        "INTEREST_RATE_SWAP",
    }


def test_policy_fair_value_and_cash_flow_surfaces_are_not_family_regions() -> None:
    for labels in (
        (
            "TÓM TẮT CÁC CHÍNH SÁCH KẾ TOÁN CHỦ YẾU",
            "Công cụ tài chính phái sinh và kế toán phòng ngừa rủi ro",
            "Các hợp đồng kỳ hạn và hoán đổi tiền tệ",
        ),
        (
            "Giá trị hợp lý của các công cụ tài chính",
            "Các công cụ tài chính phái sinh",
            "Giao dịch hoán đổi lãi suất",
        ),
        (
            "Thu từ các công cụ tài chính phái sinh tiền tệ",
            "Chi về các công cụ tài chính phái sinh tiền tệ",
            "Thu từ các công cụ tài chính phái sinh khác",
        ),
    ):
        result = topology_v1.build_accounting_family_topology_scan_v1([_page(*labels)], _spec())
        assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"


def test_exact_owner_without_structural_child_is_not_presence_evidence() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÔNG NỢ TÀI CHÍNH KHÁC",
                "Giá trị hợp lý",
                "Tài sản",
                "Công nợ",
            )
        ],
        _spec(),
    )
    assert result["status"] == "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY"
    assert result["near_regions"]


def test_one_child_can_anchor_only_beneath_the_explicit_family_owner() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÔNG NỢ TÀI CHÍNH KHÁC",
                "1 - Công cụ tài chính phái sinh tiền tệ",
            )
        ],
        _spec(),
    )
    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["minimal_unique_anchor"] == {
        "combination_size": 2,
        "pair_before_triple_search": True,
        "selected_roles": [
            "PARENT:DERIVATIVE_FINANCIAL_INSTRUMENTS",
            "CHILD:CURRENCY_DERIVATIVE_GROUP",
        ],
    }
    assert result["regions"][0]["observed_roles"] == [
        "CURRENCY_DERIVATIVE_GROUP",
    ]


def test_ocr_dropped_heading_punctuation_keeps_generic_enumeration_semantics() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "2 CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC TÀI SẢN(CÔNG NỢ) TÀI CHÍNH KHÁC",
                "Công cụ tài chính phái sinh tiền tệ",
            )
        ],
        _spec(),
    )
    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["parent_match"]["match_kind"] == (
        "EXACT_ACCENTLESS_ALIAS_AFTER_BARE_NUMERIC_HEADING_PREFIX"
    )


def test_exact_owner_variant_with_liability_wording_is_supported() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ NỢ PHẢI TRẢ TÀI CHÍNH KHÁC",
                "Giao dịch kỳ hạn tiền tệ",
            )
        ],
        _spec(),
    )
    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"


def test_numeric_cells_from_prior_row_never_expand_the_next_label_geometry() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÔNG NỢ TÀI CHÍNH KHÁC",
                "Giao dịch kỳ hạn tiền tệ",
                "(31.284)",
                "(31.284)",
                "Giao dịch hoán đổi tiền tệ",
            )
        ],
        _spec(),
    )
    swap = next(
        item for item in result["regions"][0]["child_matches"] if item["role"] == "CURRENCY_SWAP"
    )
    assert swap["source_line_index"] == swap["end_source_line_index"] == 4
    assert swap["surface"] == "Giao dịch hoán đổi tiền tệ"


def test_comma_numbered_next_family_is_a_structural_reset() -> None:
    result = topology_v1.build_accounting_family_topology_scan_v1(
        [
            _page(
                "3. CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÔNG NỢ TÀI CHÍNH KHÁC",
                "Giao dịch kỳ hạn tiền tệ",
                "4, CHO VAY KHÁCH HÀNG:",
                "30/09/2025",
                "31/12/2024",
            )
        ],
        _spec(),
    )
    assert result["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert result["regions"][0]["cluster_end_source_line_index_exclusive"] == 2


def test_repeated_period_blocks_expand_every_role_without_weakening_unique_region() -> None:
    pages = [
        _page(
            "CÁC CÔNG CỤ TÀI CHÍNH PHÁI SINH VÀ CÁC KHOẢN NỢ TÀI CHÍNH KHÁC",
            "Tại ngày 30/06/2026",
            "Giao dịch kỳ hạn tiền tệ",
            "Giao dịch hoán đổi tiền tệ",
            "Giao dịch hoán đổi lãi suất",
            "Tại ngày 31/12/2025",
            "Giao dịch kỳ hạn tiền tệ",
            "Giao dịch hoán đổi tiền tệ",
            "Giao dịch hoán đổi lãi suất",
        )
    ]
    scan = topology_v1.build_accounting_family_topology_scan_v1(pages, _spec())
    assert scan["status"] == "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL"
    assert scan["regions"][0]["observed_roles"] == [
        "FORWARD_CURRENCY",
        "CURRENCY_SWAP",
        "INTEREST_RATE_SWAP",
    ]

    occurrences = topology_v1.enumerate_accounting_family_role_occurrences_v1(
        pages,
        _spec(),
        scan["regions"][0],
    )
    assert [(item["role"], item["role_occurrence_ordinal"]) for item in occurrences] == [
        ("FORWARD_CURRENCY", 0),
        ("CURRENCY_SWAP", 0),
        ("INTEREST_RATE_SWAP", 0),
        ("FORWARD_CURRENCY", 1),
        ("CURRENCY_SWAP", 1),
        ("INTEREST_RATE_SWAP", 1),
    ]

    forged = json.loads(json.dumps(scan["regions"][0]))
    forged["cluster_end_document_line_ordinal_exclusive"] -= 1
    try:
        topology_v1.enumerate_accounting_family_role_occurrences_v1(
            pages,
            _spec(),
            forged,
        )
    except topology_v1.AccountingFamilyTopologyV1Error:
        pass
    else:
        raise AssertionError("a caller-shortened role-occurrence region was accepted")
