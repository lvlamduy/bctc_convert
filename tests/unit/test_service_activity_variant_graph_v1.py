from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/service_activity_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("service_activity_variant_graph_v1", _PATH)
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


def _trailing() -> list[str]:
    return [
        "Lãi thuần từ hoạt động dịch vụ",
        "6 tháng đầu năm 2026",
        "6 tháng đầu năm 2025",
        "Triệu đồng",
        "Thu nhập từ hoạt động dịch vụ",
        "Thu từ dịch vụ thanh toán và ngân quỹ",
        "100",
        "90",
        "Thu các dịch vụ khác",
        "20",
        "10",
        "120",
        "100",
        "Chi phí hoạt động dịch vụ",
        "Chi về dịch vụ thanh toán và ngân quỹ",
        "(30)",
        "(20)",
        "Chi các dịch vụ khác",
        "(10)",
        "(5)",
        "(40)",
        "(25)",
        "Lãi thuần từ hoạt động dịch vụ",
        "80",
        "75",
        "Lãi thuần từ hoạt động kinh doanh ngoại hối",
    ]


def test_trailing_totals_form_one_unique_graph() -> None:
    result = matcher.build_service_activity_variant_graph_document_v1([_page(_trailing())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    layout = result["regions"][0]["layout"]
    assert layout["income_parent_total_position"] == ("TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN")
    assert layout["expense_parent_total_position"] == ("TRAILING_UNLABELED_TOTAL_AFTER_CHILDREN")
    assert result["regions"][0]["pair_anchor_combinations"]


def test_leading_totals_and_reordered_optional_children_use_same_graph() -> None:
    texts = _trailing()
    income = texts[4:13]
    expense = texts[13:22]
    leading = [
        *texts[:4],
        income[0],
        *income[-2:],
        *income[5:7],
        *income[1:5],
        expense[0],
        *expense[-2:],
        *expense[5:7],
        *expense[1:5],
        *texts[22:],
    ]
    result = matcher.build_service_activity_variant_graph_document_v1([_page(leading)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    layout = result["regions"][0]["layout"]
    assert layout["income_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"
    assert layout["expense_parent_total_position"] == "LEADING_PARENT_TOTAL_BEFORE_CHILDREN"


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Thu nhập từ hoạt động dịch vụ",
            "100",
            "90",
            "Chi phí hoạt động dịch vụ",
            "(20)",
            "(10)",
            "Lãi thuần từ hoạt động dịch vụ",
            "80",
            "80",
        ],
        [
            "Lãi thuần từ hoạt động dịch vụ",
            "Thu nhập từ hoạt động dịch vụ",
            "100",
            "Chi phí hoạt động dịch vụ",
            "(20)",
            "Báo cáo bộ phận theo lĩnh vực kinh doanh",
        ],
    ],
)
def test_statement_or_segment_totals_are_negative_controls(texts: list[str]) -> None:
    result = matcher.build_service_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_trailing())]
    value = matcher.build_service_activity_variant_graph_document_v1(pages)
    forged = copy.deepcopy(value)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "savgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.ServiceActivityVariantGraphV1Error, match="replay exactly"):
        matcher.validate_service_activity_variant_graph_replay_v1(forged, pages)
