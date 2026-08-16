from __future__ import annotations

import copy
import importlib.util
import pickle
import sys
from pathlib import Path

import pytest


def _module():
    path = Path("scripts/experiments/purchased_debt_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location("purchased_debt_variant_graph_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


graph = _module()


def _page(sequence: int, texts: list[str]) -> dict:
    return {
        "lines": [
            {
                "bbox": [20, 20 + index * 20, 300, 36 + index * 20],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": sequence,
        "primary_numeric_authority": False,
    }


def _cluster(*, foreign: bool = False, reorder: bool = False) -> list[str]:
    children = ["Mua nợ bằng VND"]
    if foreign:
        children.append("Mua nợ bằng ngoại tệ")
    children.extend(["Dự phòng rủi ro", "Nợ gốc đã mua", "Lãi của khoản nợ đã mua"])
    if reorder:
        children[0:2] = reversed(children[0:2])
    return [
        "Hoạt động mua nợ",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Triệu đồng",
        *children,
        "100",
        "90",
        "(5)",
        "(4)",
        "95",
        "86",
        "Phân tích chất lượng hoạt động mua nợ",
        "Chứng khoán đầu tư",
    ]


@pytest.mark.parametrize("foreign,reorder", [(False, False), (True, False), (True, True)])
def test_complete_cluster_is_unique_and_sibling_order_is_flexible(
    foreign: bool, reorder: bool
) -> None:
    pages = [_page(1, _cluster(foreign=foreign, reorder=reorder))]
    result = graph.build_purchased_debt_variant_graph_document_v1(pages)
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["complete_region_count"] == 1
    region = result["regions"][0]
    assert region["boundary"]["first_item"]["surface"] == "Hoạt động mua nợ"
    assert region["boundary"]["last_schema_item"]["surface"] == "Lãi của khoản nợ đã mua"
    assert region["boundary"]["next_family"]["surface"] == "Chứng khoán đầu tư"
    assert region["anchor_combination"]["selected_minimal_pair"] == ["owner", "purchase_vnd"]
    assert region["anchor_combination"]["larger_combination_used"] is False
    assert graph.validate_purchased_debt_variant_graph_replay_v1(result, pages) == result


def test_bare_balance_sheet_mention_is_only_a_near_region() -> None:
    result = graph.build_purchased_debt_variant_graph_document_v1(
        [_page(1, ["Mua nợ", "100", "90", "Chứng khoán đầu tư"])]
    )
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []
    assert result["near_regions"][0]["unresolved_reasons"][0] == (
        "BARE_MUA_NO_MENTION_NOT_FAMILY_OWNER"
    )


def test_missing_interest_or_next_boundary_fails_closed() -> None:
    missing_interest = [text for text in _cluster() if text != "Lãi của khoản nợ đã mua"]
    missing_boundary = [text for text in _cluster() if text != "Chứng khoán đầu tư"]
    wrong_later_family = [
        "Góp vốn đầu tư dài hạn" if text == "Chứng khoán đầu tư" else text for text in _cluster()
    ]
    for texts in (missing_interest, missing_boundary, wrong_later_family):
        result = graph.build_purchased_debt_variant_graph_document_v1([_page(1, texts)])
        assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
        assert result["regions"] == []


def test_duplicate_complete_cluster_is_not_unique() -> None:
    pages = [_page(1, _cluster()), _page(2, _cluster())]
    result = graph.build_purchased_debt_variant_graph_document_v1(pages)
    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["metrics"]["complete_region_count"] == 2


def test_period_axis_accepts_annual_current_and_comparative_years() -> None:
    assert graph._is_period("31 12 2025")
    assert graph._is_period("31 12 2024")


def test_fresh_text_and_typed_page_contract_fail_closed() -> None:
    pages = [_page(1, _cluster())]
    result = graph.build_purchased_debt_variant_graph_document_v1(pages)
    changed = copy.deepcopy(pages)
    changed[0]["lines"][0]["vietocr_text"] = "Khác"
    with pytest.raises(graph.PurchasedDebtVariantGraphV1Error):
        graph.validate_purchased_debt_variant_graph_replay_v1(result, changed)
    poisoned = copy.deepcopy(pages)
    poisoned[0]["primary_numeric_authority"] = 0
    with pytest.raises(graph.PurchasedDebtVariantGraphV1Error):
        graph.build_purchased_debt_variant_graph_document_v1(poisoned)
    with pytest.raises(graph.PurchasedDebtVariantGraphV1Error):
        graph.build_purchased_debt_variant_graph_document_v1(pickle.loads(pickle.dumps({})))
