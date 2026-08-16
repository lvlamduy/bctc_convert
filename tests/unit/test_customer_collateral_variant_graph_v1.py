from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/customer_collateral_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("customer_collateral_variant_graph_v1", _PATH)
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


def _direct_core() -> list[str]:
    return [
        "Giá trị sổ sách của tài sản thế chấp của khách hàng tại thời điểm cuối kỳ như sau",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Bất động sản",
        "100",
        "90",
        "Giấy tờ có giá",
        "20",
        "15",
        "Tài sản thế chấp khác",
        "30",
        "25",
        "150",
        "130",
    ]


def test_direct_customer_owner_and_two_children_are_unique() -> None:
    result = matcher.build_customer_collateral_variant_graph_document_v1([_page(_direct_core())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_child_roles"] == [
        "REAL_ESTATE",
        "VALUABLE_PAPERS",
        "OTHER_COLLATERAL",
    ]


def test_generic_note_with_customer_subparent_is_accepted() -> None:
    texts = [
        "Tài sản, giấy tờ có giá thế chấp, cầm cố và chiết khấu",
        "Của khách hàng",
        "30 tháng 6 năm 2026",
        "31 tháng 12 năm 2025",
        "triệu đồng",
        "Bất động sản",
        "100",
        "90",
        "Phương tiện vận tải",
        "20",
        "15",
        "Máy móc thiết bị",
        "30",
        "25",
        "150",
        "130",
    ]
    result = matcher.build_customer_collateral_variant_graph_document_v1([_page(texts)])
    assert result["uniqueness"]["status"] == "UNIQUE_FULL_MATCH"
    assert result["regions"][0]["owner"]["vietocr_text"] == "Của khách hàng"


def test_own_pledged_assets_without_customer_scope_are_negative_control() -> None:
    texts = [
        "Tài sản, giấy tờ có giá đưa đi thế chấp, cầm cố",
        "30/06/2026",
        "31/12/2025",
        "triệu đồng",
        "Bất động sản",
        "100",
        "90",
        "Giấy tờ có giá",
        "20",
        "15",
        "120",
        "105",
    ]
    result = matcher.build_customer_collateral_variant_graph_document_v1([_page(texts)])
    assert result["metrics"] == {
        "complete_region_count": 0,
        "near_region_count": 0,
        "page_count_with_complete_region": 0,
    }


def test_incomplete_customer_region_is_retained_as_near() -> None:
    result = matcher.build_customer_collateral_variant_graph_document_v1(
        [_page(_direct_core()[:7])]
    )
    assert result["metrics"]["complete_region_count"] == 0
    assert result["metrics"]["near_region_count"] == 1


def test_two_complete_regions_are_not_unique() -> None:
    result = matcher.build_customer_collateral_variant_graph_document_v1(
        [_page(_direct_core(), 1), _page(_direct_core(), 2)]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "MULTIPLE_FULL_MATCHES",
    }
