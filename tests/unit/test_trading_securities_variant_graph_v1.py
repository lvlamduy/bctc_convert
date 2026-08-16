from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/trading_securities_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("trading_securities_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
securities = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = securities
_SPEC.loader.exec_module(securities)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (280 if x < 500 else 110), y + 20],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _issuer_table(*, reordered_children: bool = False) -> list[tuple[str, int, int]]:
    debt_children = [
        ("Chứng khoán Chính phủ", 0, 100),
        ("Chứng khoán do các TCTD khác trong nước phát hành", 0, 130),
        ("Chứng khoán do các TCKT trong nước phát hành", 0, 160),
    ]
    if reordered_children:
        debt_children = [debt_children[2], debt_children[0], debt_children[1]]
    surfaces: list[tuple[str, int, int]] = [
        ("8. CHỨNG KHOÁN KINH DOANH", 0, 0),
        ("30/06/2026", 620, 30),
        ("31/12/2025", 790, 30),
        ("Triệu đồng", 620, 55),
        ("Triệu đồng", 790, 55),
        ("Chứng khoán nợ", 0, 80),
    ]
    for ordinal, (label, x, y) in enumerate(debt_children, 1):
        surfaces.extend([(label, x, y), (str(ordinal * 10), 620, y), ("1", 790, y)])
    surfaces.extend(
        [
            ("Chứng khoán vốn", 0, 200),
            ("Do các TCTD khác trong nước phát hành", 0, 230),
            ("20", 620, 230),
            ("2", 790, 230),
            ("Do các TCKT trong nước phát hành", 0, 260),
            ("30", 620, 260),
            ("3", 790, 260),
            ("90", 620, 290),
            ("6", 790, 290),
            ("Dự phòng rủi ro chứng khoán kinh doanh", 0, 330),
            ("(5)", 620, 330),
            ("(1)", 790, 330),
            ("85", 620, 370),
            ("5", 790, 370),
            ("Dự phòng chứng khoán kinh doanh", 0, 430),
            ("Số dư đầu kỳ", 0, 470),
            ("5", 620, 470),
        ]
    )
    return surfaces


def _listing_table() -> list[tuple[str, int, int]]:
    return [
        ("Chứng khoán kinh doanh", 0, 0),
        ("30/06/2026", 620, 30),
        ("31/12/2025", 790, 30),
        ("Triệu đồng", 620, 55),
        ("Triệu đồng", 790, 55),
        ("Chứng khoán nợ", 0, 80),
        ("Đã niêm yết", 0, 110),
        ("10", 620, 110),
        ("1", 790, 110),
        ("Chưa niêm yết", 0, 140),
        ("20", 620, 140),
        ("2", 790, 140),
        ("Chứng khoán vốn", 0, 180),
        ("Đã niêm yết", 0, 210),
        ("30", 620, 210),
        ("3", 790, 210),
        ("Chưa niêm yết", 0, 240),
        ("40", 620, 240),
        ("4", 790, 240),
        ("100", 620, 280),
        ("10", 790, 280),
        ("Dự phòng giảm giá chứng khoán kinh doanh", 0, 320),
        ("(5)", 620, 320),
        ("(1)", 790, 320),
        ("95", 620, 360),
        ("9", 790, 360),
    ]


def test_issuer_variant_preserves_cluster_boundaries_order_and_meaningful_axes() -> None:
    result = securities.build_trading_securities_variant_graph_document_v1(
        [_page(_issuer_table(reordered_children=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["cluster_boundary"] == {
        "first_item_role": "TRADING_SECURITIES_OWNER",
        "first_page_sequence": 1,
        "first_source_line_index": 0,
        "last_item_role": "NET",
        "last_page_sequence": 1,
        "last_source_line_index": 28,
        "selection_rule": (
            "OWNER_THEN_REQUIRED_DEBT_EQUITY_PROVISION_PARENTS_THROUGH_LAST_"
            "NET_OR_PROVISION_ITEM_BEFORE_DISTINCT_NEXT_FAMILY"
        ),
    }
    assert region["parent_roles_in_pdf_order"] == ["DEBT", "EQUITY", "PROVISION"]
    child_roles = [event["role"] for event in region["events"] if event["role_kind"] == "CHILD"]
    assert child_roles[:3] == ["DOMESTIC_TCKT", "GOVERNMENT", "TCTD"]
    assert region["layout"]["branch_variant"] == "ISSUER_CLASSIFICATION"
    assert region["layout"]["meaningful_axes"]["percentage_values_are_non_money_auxiliary"]
    assert region["minimal_anchor"]["combination_size"] == 2
    assert any(
        item["negative_family"] == "DISTINCT_TRADING_SECURITIES_PROVISION_MOVEMENT_SUBFAMILY"
        for item in result["near_regions"]
    )


def test_listed_unlisted_variant_is_same_family_not_bank_specific_parser() -> None:
    result = securities.build_trading_securities_variant_graph_document_v1(
        [_page(_listing_table())]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["branch_variant"] == "LISTED_UNLISTED_CLASSIFICATION"
    assert [event["role"] for event in region["events"] if event["role_kind"] == "CHILD"] == [
        "LISTED",
        "UNLISTED",
        "LISTED",
        "UNLISTED",
    ]


def test_annual_2025_and_2024_period_headers_use_the_same_generic_graph() -> None:
    surfaces = [
        (
            "31/12/2025"
            if text == "30/06/2026"
            else "31/12/2024"
            if text == "31/12/2025"
            else text,
            x,
            y,
        )
        for text, x, y in _issuer_table()
    ]
    result = securities.build_trading_securities_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["meaningful_axes"]["period_header_count"] == 2


def test_accounting_policy_narrative_and_investment_securities_are_negative_controls() -> None:
    narrative = [
        ("Chứng khoán kinh doanh", 0, 0),
        (
            "Chứng khoán kinh doanh bao gồm chứng khoán nợ và chứng khoán vốn được mua chủ yếu",
            0,
            40,
        ),
        (
            "Chứng khoán nợ kinh doanh được ghi nhận theo giá gốc trừ đi dự phòng giảm giá",
            0,
            80,
        ),
        ("Dự phòng rủi ro chứng khoán kinh doanh bao gồm dự phòng tín dụng", 0, 120),
        ("Chứng khoán vốn kinh doanh chưa niêm yết được xác định theo giá", 0, 160),
        ("Chứng khoán đầu tư sẵn sàng để bán", 0, 220),
    ]
    result = securities.build_trading_securities_variant_graph_document_v1([_page(narrative)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert any(
        item["negative_family"] == "DISTINCT_INVESTMENT_SECURITIES_SUBFAMILY"
        for item in result["near_regions"]
    )


def test_exact_replay_rejects_coordinated_boundary_tamper() -> None:
    pages = [_page(_listing_table())]
    result = securities.build_trading_securities_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["cluster_boundary"]["last_item_role"] = "PROVISION"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "tsvgv1:region:" + securities.canonical_json_sha256_v1(
        region_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "tsvgv1:result:" + securities.canonical_json_sha256_v1(result_material)

    with pytest.raises(securities.TradingSecuritiesVariantGraphV1Error, match="replay exactly"):
        securities.validate_trading_securities_variant_graph_replay_v1(forged, pages)


def test_typed_inputs_and_complete_page_order_fail_closed() -> None:
    poisoned = _page(_listing_table())
    poisoned["primary_numeric_authority"] = 0
    with pytest.raises(securities.TradingSecuritiesVariantGraphV1Error, match="exact bool"):
        securities.build_trading_securities_variant_graph_document_v1([poisoned])

    skipped = _page(_listing_table(), page_sequence=2)
    with pytest.raises(securities.TradingSecuritiesVariantGraphV1Error, match="gap-free"):
        securities.build_trading_securities_variant_graph_document_v1([skipped])
