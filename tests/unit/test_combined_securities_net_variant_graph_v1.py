from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/combined_securities_net_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("combined_securities_net_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
    def bbox(index: int) -> list[int]:
        if index == 13:
            return [900, 300, 990, 320]
        if index == 14:
            return [1050, 300, 1170, 320]
        return [50, index * 25, 750, index * 25 + 20]

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


def _texts() -> list[str]:
    return [
        "4.",
        "Lãi thuần từ chứng khoán kinh doanh, chứng khoán đầu tư",
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Lãi/(lỗ) thuần từ mua bán chứng khoán kinh doanh",
        "249.524",
        "415.700",
        "Lãi/(lỗ) thuần từ mua bán chứng khoán đầu tư",
        "3.587",
        "1.295.273",
        "Lãi thuần từ chứng khoán kinh doanh, chứng",
        "khoán đầu tư",
        "253.111",
        "1.710.973",
        "5. Lãi thuần từ hoạt động kinh doanh khác",
    ]


def test_section_heading_is_near_and_wrapped_numeric_total_is_unique() -> None:
    result = matcher.build_combined_securities_net_variant_graph_document_v1([_page(_texts())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"] == {
        "complete_region_count": 1,
        "near_region_count": 1,
        "two_value_region_count": 1,
        "wrapped_complete_region_count": 1,
    }
    assert result["regions"][0]["value_lines"][0]["source_line_index"] == 13


def test_heading_without_two_values_cannot_accept() -> None:
    result = matcher.build_combined_securities_net_variant_graph_document_v1([_page(_texts()[:11])])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["near_region_count"] == 1


def test_two_numeric_totals_are_not_unique() -> None:
    result = matcher.build_combined_securities_net_variant_graph_document_v1(
        [_page(_texts()), _page(_texts(), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_public_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_texts())]
    result = matcher.build_combined_securities_net_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["page_span"] = [2, 2]
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "csnvgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.CombinedSecuritiesNetVariantGraphV1Error, match="replay exactly"):
        matcher.validate_combined_securities_net_variant_graph_replay_v1(forged, pages)
