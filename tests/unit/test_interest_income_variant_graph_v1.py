from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/interest_income_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("interest_income_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
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
        "page_sequence": 1,
        "primary_numeric_authority": True,
    }


def _children() -> list[str]:
    return [
        "Thu nhập lãi tiền gửi",
        "100",
        "90",
        "Thu nhập lãi cho vay khách hàng",
        "500",
        "450",
        "Thu lãi từ kinh doanh, đầu tư chứng khoán",
        "80",
        "70",
        "Thu phí từ nghiệp vụ bảo lãnh",
        "20",
        "10",
    ]


def test_trailing_total_variant_is_unique() -> None:
    result = matcher.build_interest_income_variant_graph_document_v1(
        [
            _page(
                [
                    "Thu nhập lãi và các khoản thu nhập tương tự",
                    "30.6.2026",
                    "30.6.2025",
                    "Triệu đồng",
                    *_children(),
                    "700",
                    "620",
                    "Chi phí lãi và các chi phí tương tự",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["printed_parent_total_position"] == (
        "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    )
    assert {"DEPOSIT_INTEREST", "CUSTOMER_LOAN_INTEREST"}.issubset(region["layout"]["child_roles"])
    assert region["pair_anchor_combinations"]


def test_parent_total_may_precede_children_and_axes_may_precede_owner() -> None:
    result = matcher.build_interest_income_variant_graph_document_v1(
        [
            _page(
                [
                    "Sáu tháng đầu năm 2026",
                    "Sáu tháng đầu năm 2025",
                    "Triệu VND",
                    "Thu nhập lãi và các khoản thu nhập tương tự",
                    "700",
                    "620",
                    *_children(),
                    "Chi phí lãi và các chi phí tương tự",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["printed_parent_total_position"] == (
        "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    )


def test_optional_rows_and_child_order_are_not_bank_rules() -> None:
    texts = [
        "Thu nhập lãi và các khoản thu nhập tương tự",
        "Kỳ này",
        "Kỳ trước",
        "Triệu đồng",
        "Thu khác từ hoạt động tín dụng",
        "10",
        "9",
        "Thu nhập lãi cho vay",
        "500",
        "450",
        "Thu nhập lãi từ nghiệp vụ mua bán nợ",
        "5",
        "4",
        "Thu lãi tiền gửi",
        "100",
        "90",
        "615",
        "553",
    ]
    result = matcher.build_interest_income_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert "PURCHASED_DEBT_INTEREST" in result["regions"][0]["layout"]["child_roles"]


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Thu nhập lãi và các khoản thu nhập tương tự",
            "30.6.2026",
            "30.6.2025",
            "Triệu đồng",
            "100",
            "90",
        ],
        [
            "Thu nhập lãi và các khoản thu nhập tương tự",
            "30.6.2026",
            "30.6.2025",
            "Triệu đồng",
            "Thu lãi tiền gửi",
            "100",
            "90",
            "Thu lãi cho vay",
            "500",
            "450",
        ],
    ],
)
def test_statement_or_incomplete_table_is_negative_control(texts: list[str]) -> None:
    result = matcher.build_interest_income_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [
        _page(
            [
                "Thu nhập lãi và các khoản thu nhập tương tự",
                "30.6.2026",
                "30.6.2025",
                "Triệu đồng",
                *_children(),
                "700",
                "620",
            ]
        )
    ]
    result = matcher.build_interest_income_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "iivgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.InterestIncomeVariantGraphV1Error, match="replay exactly"):
        matcher.validate_interest_income_variant_graph_replay_v1(forged, pages)
