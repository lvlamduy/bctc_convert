from __future__ import annotations

import copy
import importlib.util
import pickle
import re
import sys
from pathlib import Path

import pytest


def _module():
    path = Path("scripts/experiments/investment_securities_variant_graph_v1.py")
    spec = importlib.util.spec_from_file_location("investment_securities_variant_graph_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


graph = _module()
_NUMBER = re.compile(r"^\(?[0-9.,]+\)?$")


def _page(sequence: int, texts: list[str]) -> dict:
    lines = []
    for index, text in enumerate(texts):
        numeric = bool(_NUMBER.fullmatch(text))
        x = 700 if numeric else 20
        lines.append(
            {
                "bbox": [x, 20 + index * 20, x + 280, 36 + index * 20],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {
        "lines": lines,
        "page_sequence": sequence,
        "primary_numeric_authority": False,
    }


def _cluster(*, owner: bool = True, debt_parent: bool = True, htm: bool = True) -> list[str]:
    texts = []
    if owner:
        texts.append("Chứng khoán đầu tư")
    texts.extend(
        [
            "Chứng khoán đầu tư sẵn sàng để bán",
            "30/06/2026",
            "31/12/2025",
            "Triệu đồng",
            "Triệu đồng",
        ]
    )
    if debt_parent:
        texts.extend(["Chứng khoán nợ", "300", "290"])
    texts.extend(
        [
            "Chứng khoán Chính phủ",
            "100",
            "90",
            "Chứng khoán nợ do các TCTD khác trong nước phát hành",
            "200",
            "200",
            "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
            "(5)",
            "(4)",
        ]
    )
    if htm:
        texts.extend(
            [
                "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                "Chứng khoán nợ",
                "Chứng khoán Chính phủ",
                "40",
                "30",
                "Chứng khoán nợ do các TCTD khác trong nước phát hành",
                "60",
                "70",
            ]
        )
    texts.append("Góp vốn, đầu tư dài hạn")
    return texts


@pytest.mark.parametrize(
    "owner,debt_parent,expected_mode,expected_pair",
    [
        (True, True, "EXPLICIT_FAMILY_OWNER", ["afs", "afs_debt"]),
        (True, False, "EXPLICIT_FAMILY_OWNER", ["afs", "afs_government"]),
        (False, True, "IMPLICIT_OWNER_UNIQUE_AFS_CORE", ["afs", "afs_debt"]),
    ],
)
def test_core_variants_are_unique_and_pair_first(
    owner: bool, debt_parent: bool, expected_mode: str, expected_pair: list[str]
) -> None:
    pages = [_page(1, _cluster(owner=owner, debt_parent=debt_parent))]
    result = graph.build_investment_securities_variant_graph_document_v1(pages)
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["owner_mode"] == expected_mode
    assert region["anchor_combination"]["selected_minimal_pair"] == expected_pair
    assert region["anchor_combination"]["larger_combination_used"] is False
    assert region["boundary"]["next_family"]["surface"] == "Góp vốn, đầu tư dài hạn"
    assert graph.validate_investment_securities_variant_graph_replay_v1(result, pages) == result


def test_htm_quality_and_vamc_are_optional_not_required_core() -> None:
    texts = _cluster(htm=False)
    texts[-1:-1] = [
        "Phân tích chất lượng chứng khoán đầu tư sẵn sàng để bán",
        "Mệnh giá trái phiếu VAMC",
        "50",
        "Dự phòng trái phiếu VAMC",
        "(2)",
    ]
    result = graph.build_investment_securities_variant_graph_document_v1([_page(1, texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert "quality" in result["regions"][0]["anchors"]
    assert "htm" not in result["regions"][0]["anchors"]


def test_accounting_policy_text_without_aligned_values_is_only_near() -> None:
    texts = [
        "Chứng khoán đầu tư sẵn sàng để bán",
        "Chứng khoán nợ do Chính phủ phát hành được ghi nhận theo giá gốc",
        "Chứng khoán nợ do các TCTD khác phát hành được phân loại",
        "30/06/2026",
        "31/12/2025",
        "Góp vốn, đầu tư dài hạn",
    ]
    result = graph.build_investment_securities_variant_graph_document_v1([_page(1, texts)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert all(
        "TWO_AFS_ISSUER_CHILDREN_NOT_RESOLVED" in region["unresolved_reasons"]
        for region in result["near_regions"]
    )


def test_missing_next_boundary_and_duplicate_regions_fail_closed() -> None:
    no_boundary = [text for text in _cluster() if text != "Góp vốn, đầu tư dài hạn"]
    assert (
        graph.build_investment_securities_variant_graph_document_v1([_page(1, no_boundary)])[
            "status"
        ]
        == "UNRESOLVED_NO_COMPLETE_REGION"
    )
    duplicate = graph.build_investment_securities_variant_graph_document_v1(
        [_page(1, _cluster()), _page(2, _cluster())]
    )
    assert duplicate["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"


def test_period_axis_accepts_annual_current_and_comparative_years() -> None:
    assert graph._is_period("31 12 2025")
    assert graph._is_period("31 12 2024")


def test_fresh_text_and_typed_page_contract_fail_closed() -> None:
    pages = [_page(1, _cluster())]
    result = graph.build_investment_securities_variant_graph_document_v1(pages)
    changed = copy.deepcopy(pages)
    changed[0]["lines"][0]["vietocr_text"] = "Khác"
    with pytest.raises(graph.InvestmentSecuritiesVariantGraphV1Error):
        graph.validate_investment_securities_variant_graph_replay_v1(result, changed)
    poisoned = copy.deepcopy(pages)
    poisoned[0]["primary_numeric_authority"] = 0
    with pytest.raises(graph.InvestmentSecuritiesVariantGraphV1Error):
        graph.build_investment_securities_variant_graph_document_v1(poisoned)
    with pytest.raises(graph.InvestmentSecuritiesVariantGraphV1Error):
        graph.build_investment_securities_variant_graph_document_v1(pickle.loads(pickle.dumps({})))
