from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/securities_sale_activity_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("securities_sale_activity_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [50, index * 25, 750, index * 25 + 20],
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


def _trading_texts() -> list[str]:
    return [
        "16. Lãi/(lỗ) thuần từ hoạt động mua bán chứng khoán kinh doanh",
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Thu nhập từ mua bán chứng khoán kinh doanh",
        "205.951",
        "648.456",
        "Chi phí về mua bán chứng khoán kinh doanh",
        "(90.303)",
        "(17.821)",
        "Trích lập dự phòng rủi ro chứng khoán đầu tư",
        "(178.762)",
        "-",
        "(63.114)",
        "630.635",
        "17. Lãi/(lỗ) thuần từ mua bán chứng khoán đầu tư",
    ]


def test_trading_profile_accepts_optional_mislabelled_provision_by_structure() -> None:
    result = matcher.build_securities_sale_activity_variant_graph_document_v1(
        [_page(_trading_texts())], family_variant="TRADING_SECURITIES"
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["child_roles"] == [
        "EXPENSE",
        "INCOME",
        "PROVISION",
    ]


def test_investment_profile_is_a_distinct_negative_control_for_trading() -> None:
    texts = [text.replace("kinh doanh", "đầu tư") for text in _trading_texts()[:-1]]
    trading = matcher.build_securities_sale_activity_variant_graph_document_v1(
        [_page(texts)], family_variant="TRADING_SECURITIES"
    )
    investment = matcher.build_securities_sale_activity_variant_graph_document_v1(
        [_page(texts)], family_variant="INVESTMENT_SECURITIES"
    )
    assert trading["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert investment["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_wrapped_trading_owner_and_optional_provision_absence_are_admitted() -> None:
    texts = [
        "Lãi/(lỗ) thuần từ mua bán chứng khoán kinh",
        "doanh",
        "Kỳ này",
        "Kỳ trước",
        "Triệu đồng",
        "Thu nhập từ mua bán chứng khoán kinh doanh",
        "630.564",
        "580.842",
        "Chi về mua bán chứng khoán kinh doanh",
        "(385.263)",
        "(132.711)",
        "249.524",
        "448.131",
        "Lãi/(lỗ) thuần từ mua bán chứng khoán đầu tư",
    ]
    result = matcher.build_securities_sale_activity_variant_graph_document_v1(
        [_page(texts)], family_variant="TRADING_SECURITIES"
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"


def test_statement_total_policy_and_incomplete_rows_remain_near_or_negative() -> None:
    pages = [
        _page(
            [
                "Lãi thuần từ mua bán chứng khoán kinh doanh",
                "100",
                "90",
            ]
        ),
        _page(
            [
                "Chứng khoán kinh doanh",
                "Chứng khoán kinh doanh được ghi nhận theo giá gốc",
                "Dự phòng giảm giá chứng khoán kinh doanh",
            ],
            2,
        ),
    ]
    result = matcher.build_securities_sale_activity_variant_graph_document_v1(
        pages, family_variant="TRADING_SECURITIES"
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["near_region_count"] == 1


def test_two_complete_regions_are_not_unique() -> None:
    result = matcher.build_securities_sale_activity_variant_graph_document_v1(
        [_page(_trading_texts()), _page(_trading_texts(), 2)],
        family_variant="TRADING_SECURITIES",
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_trading_texts())]
    value = matcher.build_securities_sale_activity_variant_graph_document_v1(
        pages, family_variant="TRADING_SECURITIES"
    )
    forged = copy.deepcopy(value)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ssav1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.SecuritiesSaleActivityVariantGraphV1Error, match="replay exactly"):
        matcher.validate_securities_sale_activity_variant_graph_replay_v1(
            forged, pages, family_variant="TRADING_SECURITIES"
        )


@pytest.mark.parametrize("bad", [None, 1, "TRADING", "trading_securities"])
def test_profile_is_closed_and_exact_typed(bad: object) -> None:
    with pytest.raises(
        matcher.SecuritiesSaleActivityVariantGraphV1Error,
        match="family variant",
    ):
        matcher.build_securities_sale_activity_variant_graph_document_v1(
            [_page(_trading_texts())], family_variant=bad
        )
