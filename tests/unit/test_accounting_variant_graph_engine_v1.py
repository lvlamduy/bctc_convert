from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_variant_graph_engine_v1 import (
    AccountingVariantGraphEngineV1Error,
    build_accounting_variant_region_scan_v1,
    normalize_vietnamese_anchor_v1,
    validate_accounting_variant_region_scan_replay_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _spec() -> dict[str, object]:
    return {
        "branch_core_phrases": ["phân tích", "dư nợ"],
        "branch_variants": [
            {"anchor_phrase": "thời hạn gốc", "variant_id": "ORIGINAL_TERM"},
            {"anchor_phrase": "thời gian", "variant_id": "TIME"},
        ],
        "family_id": "LOAN_MATURITY_BUCKETS",
        "format_version": "ACCOUNTING_VARIANT_FAMILY_SPEC_V1",
        "limits": {
            "max_branch_to_last_child_line_span": 32,
            "max_child_gap": 12,
            "min_numeric_followers_per_child": 2,
        },
        "optional_intermediate_aliases": ["Dư nợ cho vay"],
        "ordered_children": [
            {"aliases": ["Nợ ngắn hạn", "Cho vay ngắn hạn"], "role": "SHORT_TERM"},
            {"aliases": ["Nợ trung hạn", "Cho vay trung hạn"], "role": "MEDIUM_TERM"},
            {"aliases": ["Nợ dài hạn", "Cho vay dài hạn"], "role": "LONG_TERM"},
        ],
        "owner_aliases": ["Cho vay khách hàng", "Dư nợ cho vay khách hàng"],
    }


def _page(page_sequence: int, surfaces: list[str]) -> dict[str, object]:
    return {
        "lines": [
            {"source_line_index": index, "vietocr_text": text}
            for index, text in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
    }


def _complete_surface(*, branch: str = "Phân tích dư nợ theo thời gian") -> list[str]:
    return [
        branch,
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Triệu đồng",
        "Dư nợ cho vay",
        "Nợ ngắn hạn",
        "10",
        "11",
        "Nợ trung hạn",
        "20",
        "21",
        "Nợ dài hạn",
        "30",
        "31",
        "60",
        "63",
    ]


def test_generic_engine_enumerates_complete_and_near_regions_without_bank_routing():
    pages = [
        _page(1, ["5. Cho vay khách hàng"]),
        _page(2, _complete_surface()),
        _page(3, ["Phân tích dư nợ theo nhóm nợ", "Nợ đủ tiêu chuẩn"]),
        _page(
            4,
            [
                "Cho vay khách hàng",
                "Phân tích dư nợ theo thời gian",
                "Nợ ngắn hạn",
                "1",
                "2",
                "Nợ trung hạn",
                "3",
                "4",
            ],
        ),
        _page(5, ["Phân tích chất lượng nợ cho vay", "Nợ ngắn hạn"]),
    ]

    result = build_accounting_variant_region_scan_v1(pages, _spec())

    assert result["metrics"] == {
        "complete_context_region_count": 1,
        "near_region_count": 2,
        "ordered_anchor_region_count": 1,
    }
    region = result["regions"][0]
    assert region["page_sequence"] == 2
    assert region["owner_context"]["mode"] == "IMMEDIATE_PREVIOUS_PAGE"
    assert [item["role"] for item in region["child_match_records"]] == [
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
    ]
    assert region["optional_intermediate_matches"][0]["surface"] == "Dư nợ cho vay"
    assert result["safety"]["bank_filename_note_or_page_used_for_matching"] is False
    assert result["safety"]["text_similarity_alone_can_accept"] is False
    assert {tuple(item["unresolved_reasons"]) for item in result["near_regions"]} == {
        ("BRANCH_VARIANT_NOT_RESOLVED",),
        ("MISSING_ORDERED_CHILD_LONG_TERM",),
    }


def test_accent_normalization_and_one_character_error_stay_bounded_by_topology():
    assert normalize_vietnamese_anchor_v1("Nợ trùng hạn") == "no trung han"
    page = _complete_surface(branch="Phân tíh dư nợ theo thời gian")
    page[9] = "Nợ trungg hạn"
    result = build_accounting_variant_region_scan_v1(
        [_page(1, ["Cho vay khách hàng", *page])], _spec()
    )

    assert result["metrics"]["ordered_anchor_region_count"] == 1
    region = result["regions"][0]
    assert region["branch_match"]["match_kind"] == (
        "ONE_EDIT_STRUCTURAL_ANCHORS_IN_COMPLETE_TOPOLOGY"
    )
    assert region["child_match_records"][1]["match_kind"] == (
        "ONE_EDIT_ALIAS_IN_COMPLETE_ORDERED_TOPOLOGY"
    )

    page[6] = "Nợi ngắn hạn"
    rejected = build_accounting_variant_region_scan_v1(
        [_page(1, ["Cho vay khách hàng", *page])], _spec()
    )
    assert rejected["regions"][0]["context_complete"] is False
    assert "MULTIPLE_APPROXIMATE_CHILD_ROLES" in rejected["regions"][0]["unresolved_reasons"]


def test_family_without_optional_intermediate_aliases_uses_the_same_engine():
    spec = _spec()
    spec["optional_intermediate_aliases"] = []

    result = build_accounting_variant_region_scan_v1(
        [_page(1, ["Cho vay khách hàng", *_complete_surface()])], spec
    )

    assert result["metrics"]["complete_context_region_count"] == 1
    assert result["regions"][0]["optional_intermediate_matches"] == []


def test_spec_bank_field_and_coordinated_scan_rehash_fail_closed_on_replay():
    pages = [_page(1, ["Cho vay khách hàng", *_complete_surface()])]
    bad_spec = _spec() | {"bank": "MBB"}
    with pytest.raises(AccountingVariantGraphEngineV1Error):
        build_accounting_variant_region_scan_v1(pages, bad_spec)

    value = build_accounting_variant_region_scan_v1(pages, _spec())
    tampered = copy.deepcopy(value)
    tampered["regions"][0]["branch_match"]["surface"] = "Phân tích dư nợ giả"
    material = copy.deepcopy(tampered)
    material.pop("scan_id")
    tampered["scan_id"] = "avgev1:scan:" + canonical_json_sha256_v1(material)
    with pytest.raises(AccountingVariantGraphEngineV1Error):
        validate_accounting_variant_region_scan_replay_v1(tampered, pages, _spec())
