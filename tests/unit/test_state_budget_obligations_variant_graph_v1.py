from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/state_budget_obligations_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("state_budget_obligations_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
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
    return {"lines": lines, "page_sequence": 1, "primary_numeric_authority": True}


def _core(owner: str = "Tình hình thực hiện nghĩa vụ với NSNN") -> list[str]:
    return [
        owner,
        "Số dư đầu kỳ",
        "Số phải nộp",
        "Số đã nộp",
        "Số dư cuối kỳ",
        "Triệu đồng",
        "Thuế GTGT",
        "100",
        "20",
        "(10)",
        "110",
        "Thuế TNDN",
        "200",
        "50",
        "(40)",
        "210",
        "Các loại thuế khác",
        "30",
        "5",
        "(4)",
        "31",
    ]


def test_required_tax_core_is_accepted() -> None:
    result = matcher.build_state_budget_obligations_variant_graph_document_v1([_page(_core())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_tax_roles"][:3] == [
        "VAT",
        "CORPORATE_INCOME_TAX",
        "OTHER_TAX",
    ]


def test_optional_extra_lane_and_tax_children_are_accepted() -> None:
    texts = _core("Tình hình thực hiện nghĩa vụ với Ngân sách Nhà nước")
    texts[1:1] = ["Tăng do hợp nhất kinh doanh"]
    texts.extend(
        [
            "Thuế thu nhập cá nhân",
            "10",
            "2",
            "3",
            "(1)",
            "14",
            "Các khoản phí, lệ phí và phải nộp khác",
            "1",
            "0",
            "1",
            "(1)",
            "1",
        ]
    )
    result = matcher.build_state_budget_obligations_variant_graph_document_v1([_page(texts)])
    region = result["regions"][0]
    assert "BUSINESS_COMBINATION_INCREASE_AXIS" in region["layout"]["observed_axis_roles"]
    assert "PERSONAL_INCOME_TAX" in region["layout"]["observed_tax_roles"]
    assert "OTHER_PAYABLE" in region["layout"]["observed_tax_roles"]


def test_document_unit_inheritance_is_retained_as_layout_variant() -> None:
    texts = [text for text in _core() if text != "Triệu đồng"]
    result = matcher.build_state_budget_obligations_variant_graph_document_v1([_page(texts)])
    assert result["regions"][0]["layout"]["document_unit_inheritance_required"] is True


def test_annual_date_pair_resolves_opening_and_closing_without_fixed_years() -> None:
    texts = _core()
    texts[1] = "01/01/2025"
    texts[4] = "31/12/2025"

    result = matcher.build_state_budget_obligations_variant_graph_document_v1([_page(texts)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert {"OPENING_AXIS", "CLOSING_AXIS"}.issubset(
        result["regions"][0]["layout"]["observed_axis_roles"]
    )


@pytest.mark.parametrize(
    "texts",
    [
        ["Thuế TNDN hiện hành", "100", "Chi phí thuế TNDN", "100"],
        ["Tình hình thực hiện nghĩa vụ với NSNN", "Thuế GTGT", "100"],
        ["Các loại thuế khác", "100", "Thuế TNDN", "200"],
    ],
)
def test_policy_reconciliation_or_incomplete_region_does_not_accept(
    texts: list[str],
) -> None:
    result = matcher.build_state_budget_obligations_variant_graph_document_v1([_page(texts)])
    assert result["metrics"]["complete_region_count"] == 0
