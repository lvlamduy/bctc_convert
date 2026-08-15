from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/capital_contribution_dividend_income_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "capital_contribution_dividend_income_variant_graph_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
    def bbox(index: int) -> list[int]:
        if index == 0:
            return [10, 0, 35, 20]
        if index == 1:
            return [60, 0, 600, 20]
        return [60, index * 25, 700, index * 25 + 20]

    return {
        "lines": [
            {
                "bbox": bbox(index),
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


def _collapsed() -> list[str]:
    return [
        "6.",
        "Thu nhập từ góp vốn, mua cổ phần",
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Triệu đồng",
        "Thu nhập từ góp vốn, mua cổ phần",
        "24.376",
        "27.214",
        "24.376",
        "27.214",
    ]


def _split() -> list[str]:
    return [
        "18.",
        "Thu nhập từ góp vốn, mua cổ phần",
        "Kỳ này",
        "Kỳ trước",
        "Triệu VND",
        "Triệu VND",
        "Cổ tức nhận trong kỳ từ góp vốn đầu tư dài hạn",
        "4.329",
        "4.896",
        "Phân chia lãi/lỗ theo phương pháp vốn chủ sở hữu",
        "193.245",
        "91.322",
        "197.574",
        "96.218",
    ]


def test_collapsed_and_optional_equity_method_variants_accept() -> None:
    collapsed = matcher.build_capital_contribution_dividend_income_variant_graph_document_v1(
        [_page(_collapsed())]
    )
    assert collapsed["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert collapsed["regions"][0]["layout"]["child_roles"] == ["COLLAPSED_PARENT"]
    split = matcher.build_capital_contribution_dividend_income_variant_graph_document_v1(
        [_page(_split())]
    )
    assert split["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert split["regions"][0]["layout"]["child_roles"] == [
        "EQUITY_METHOD",
        "LONG_TERM_CAPITAL_DIVIDEND",
    ]


def test_statement_aggregate_without_numbered_note_axes_is_negative() -> None:
    result = matcher.build_capital_contribution_dividend_income_variant_graph_document_v1(
        [_page(["Thu nhập từ góp vốn, mua cổ phần", "200", "100", "200", "100"])]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 0


def test_two_complete_notes_are_not_unique() -> None:
    result = matcher.build_capital_contribution_dividend_income_variant_graph_document_v1(
        [_page(_collapsed()), _page(_split(), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_public_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_collapsed())]
    result = matcher.build_capital_contribution_dividend_income_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ccdvgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(
        matcher.CapitalContributionDividendIncomeVariantGraphV1Error, match="replay exactly"
    ):
        matcher.validate_capital_contribution_dividend_income_variant_graph_replay_v1(forged, pages)
