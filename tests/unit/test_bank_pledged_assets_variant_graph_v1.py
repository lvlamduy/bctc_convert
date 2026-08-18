from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/bank_pledged_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("bank_pledged_assets_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page: int = 1) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"\(?[0-9][0-9.,]*\)?", text) is not None
        lines.append(
            {
                "bbox": [750 if numeric else 60, index * 25, 920, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": page, "primary_numeric_authority": True}


def _core(*, reversed_children: bool = False) -> list[str]:
    children = [
        "Giấy tờ có giá đưa đi thế chấp, cầm cố",
        "100",
        "90",
        "Giấy tờ có giá đưa đi chiết khấu, tái chiết khấu",
        "20",
        "15",
    ]
    if reversed_children:
        children = children[3:] + children[:3]
    return [
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        *children,
        "120",
        "105",
    ]


def test_bank_own_asset_owner_and_two_source_roles_are_unique() -> None:
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1([_page(_core())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_source_roles"] == [
        "PLEDGED_VALUABLE_PAPERS",
        "DISCOUNTED_VALUABLE_PAPERS",
    ]


def test_sibling_order_is_not_a_matching_requirement() -> None:
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1(
        [_page(_core(reversed_children=True))]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }


def test_annual_current_and_comparative_years_are_derived_from_the_page() -> None:
    texts = _core()
    texts[1:3] = ["31/12/2025", "31/12/2024"]

    result = matcher.build_bank_pledged_assets_variant_graph_document_v1([_page(texts)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_customer_collateral_branch_is_a_negative_control() -> None:
    texts = [
        "Giá trị sổ sách của tài sản thế chấp của khách hàng",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Bất động sản",
        "100",
        "90",
        "Giấy tờ có giá",
        "20",
        "15",
    ]
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1([_page(texts)])
    assert result["metrics"] == {
        "complete_region_count": 0,
        "near_region_count": 0,
        "page_count_with_complete_region": 0,
    }


def test_incomplete_owned_asset_region_is_retained_as_near() -> None:
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1([_page(_core()[:6])])
    assert result["metrics"]["complete_region_count"] == 0
    assert result["metrics"]["near_region_count"] == 1


def test_owner_and_one_generic_child_can_uniquely_identify_the_family() -> None:
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
                    "31/12/2025",
                    "31/12/2024",
                    "triệu đồng",
                    "Giấy tờ có giá",
                    "4.508.464",
                    "12.260.320",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_source_roles"] == ["GENERIC_VALUABLE_PAPERS"]


def test_period_inference_is_scoped_to_the_owner_table_neighbourhood() -> None:
    preamble = [
        "Ban hành theo Thông tư số 49/2014/TT-NHNN",
        "Ngân hàng Nhà nước Việt Nam",
        "Tiền và các khoản tương đương tiền",
        "Tiền mặt",
        "Tổng cộng",
        "Báo cáo tài chính hợp nhất",
        "Cho năm tài chính",
        "Nội dung",
        "Tiếp theo",
        "Thuyết minh",
        "Bảng số liệu",
        "Thông tin bổ sung",
    ]
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1(
        [_page([*preamble, *_core()])]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_direct_schema_children_and_wrapped_debt_security_rows_are_generic() -> None:
    texts = [
        "Tài sản, GTCG đưa đi thế chấp, cầm cố và chiết khấu, tái chiết khấu",
        "31.12.2025",
        "31.12.2024",
        "Triệu VND",
        "Chứng khoán kinh doanh",
        "10",
        "-",
        "Chứng khoán đầu tư",
        "20",
        "18",
        "Tài sản cố định",
        "-",
        "1",
        "Chứng khoán Nợ đưa đi cầm cố trong giao dịch vay cầm",
        "cố các giấy tờ có giá",
        "30",
        "19",
    ]
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_source_roles"] == [
        "TRADING_SECURITIES",
        "INVESTMENT_SECURITIES",
        "FIXED_ASSETS",
        "PLEDGED_DEBT_SECURITIES",
    ]


def test_two_complete_regions_are_not_unique() -> None:
    result = matcher.build_bank_pledged_assets_variant_graph_document_v1(
        [_page(_core(), 1), _page(_core(), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "MULTIPLE_FULL_MATCHES",
    }
