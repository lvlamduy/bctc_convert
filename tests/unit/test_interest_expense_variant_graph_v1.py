from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/interest_expense_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("interest_expense_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], sequence: int = 1) -> dict[str, object]:
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
        "page_sequence": sequence,
        "primary_numeric_authority": True,
    }


def _children() -> list[str]:
    return [
        "Trả lãi tiền gửi",
        "100",
        "90",
        "Trả lãi tiền vay",
        "20",
        "10",
        "Trả lãi phát hành giấy tờ có giá",
        "30",
        "25",
        "Chi phí hoạt động tín dụng khác",
        "5",
        "4",
    ]


def test_trailing_total_variant_is_unique() -> None:
    pages = [
        _page(
            [
                "Chi phí lãi và các khoản chi phí tương tự",
                "30.6.2026",
                "30.6.2025",
                "Triệu đồng",
                *_children(),
                "155",
                "129",
                "Lãi thuần từ mua bán chứng khoán kinh doanh",
            ]
        )
    ]
    result = matcher.build_interest_expense_variant_graph_document_v1(pages)
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["printed_parent_total_position"] == (
        "TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN"
    )
    assert region["layout"]["unit_axis_scope"] == "LOCAL_PAGE_UNIT_AXIS"
    assert region["pair_anchor_combinations"]


def test_leading_total_and_reordered_optional_rows_are_generic() -> None:
    result = matcher.build_interest_expense_variant_graph_document_v1(
        [
            _page(
                [
                    "6 tháng đầu năm 2026",
                    "6 tháng đầu năm 2025",
                    "triệu đồng",
                    "Chi phí lãi và các chi phí tương tự",
                    "155",
                    "129",
                    "Chi các hoạt động tín dụng khác",
                    "5",
                    "4",
                    "Chi lãi tiền vay",
                    "20",
                    "10",
                    "Chi lãi phát hành giấy tờ có giá",
                    "30",
                    "25",
                    "Chi lãi tiền gửi",
                    "100",
                    "90",
                    "Thu nhập lãi thuần",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["printed_parent_total_position"] == (
        "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    )


def test_combined_deposit_and_borrowing_row_has_borrowing_semantics() -> None:
    texts = [
        "Chi phí lãi và các khoản chi phí tương tự",
        "từ 1/1/2026 đến 30/6/2026",
        "từ 1/1/2025 đến 30/6/2025",
        "Triệu VND",
        "Trả lãi tiền gửi",
        "100",
        "90",
        "Trả lãi tiền gửi và vay các tổ chức tín dụng khác",
        "20",
        "10",
        "Trả lãi phát hành giấy tờ có giá",
        "30",
        "25",
        "Chi phí khác cho hoạt động tín dụng",
        "5",
        "4",
        "155",
        "129",
    ]
    result = matcher.build_interest_expense_variant_graph_document_v1([_page(texts)])
    roles = result["regions"][0]["layout"]["child_roles"]
    assert roles.count("DEPOSIT_INTEREST") == 1
    assert roles.count("BORROWING_INTEREST") == 1


def test_income_finance_lease_is_not_expense_because_chinh_contains_chi() -> None:
    assert matcher._child_role("Thu lãi cho thuê tài chính") is None


def test_nearest_preceding_document_unit_is_explicit() -> None:
    previous = _page(["Đơn vị: Triệu VND"], 1)
    current = _page(
        [
            "Chi phí lãi và các chi phí tương tự",
            "Từ 01/01/2026 đến 30/06/2026",
            "Từ 01/01/2025 đến 30/06/2025",
            *_children(),
            "155",
            "129",
        ],
        2,
    )
    result = matcher.build_interest_expense_variant_graph_document_v1([previous, current])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["unit_axis_scope"] == (
        "NEAREST_PRECEDING_DOCUMENT_UNIT_AXIS"
    )


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Chi phí lãi và các khoản chi phí tương tự đã trả",
            "30.6.2026",
            "30.6.2025",
            "Triệu đồng",
            "100",
            "90",
        ],
        [
            "Chi phí lãi",
            "Chi phí lãi được ghi nhận theo cơ sở dồn tích",
            "30.6.2026",
            "30.6.2025",
            "Triệu đồng",
            *_children(),
        ],
    ],
)
def test_cash_flow_or_policy_region_is_negative_control(texts: list[str]) -> None:
    result = matcher.build_interest_expense_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [
        _page(
            [
                "Chi phí lãi và các chi phí tương tự",
                "30.6.2026",
                "30.6.2025",
                "Triệu đồng",
                *_children(),
                "155",
                "129",
            ]
        )
    ]
    result = matcher.build_interest_expense_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ievgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.InterestExpenseVariantGraphV1Error, match="replay exactly"):
        matcher.validate_interest_expense_variant_graph_replay_v1(forged, pages)
