from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/other_activity_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("other_activity_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], sequence: int = 1) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"\(?[0-9][0-9.,]*\)?", text) is not None
        x0 = 750 if numeric else 60
        lines.append(
            {
                "bbox": [x0, index * 25, x0 + 150, index * 25 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": sequence, "primary_numeric_authority": True}


def _gross(owner: str = "29. Lãi thuần từ hoạt động khác") -> list[str]:
    return [
        owner,
        "6 tháng đầu năm 2026",
        "6 tháng đầu năm 2025",
        "Triệu đồng",
        "Thu nhập từ hoạt động khác",
        "100",
        "90",
        "Thu từ các công cụ tài chính phái sinh khác",
        "60",
        "50",
        "Thu hồi nợ đã xử lý rủi ro",
        "40",
        "40",
        "Chi phí hoạt động khác",
        "(30)",
        "(20)",
        "Chi cho các công cụ tài chính phái sinh khác",
        "(20)",
        "(10)",
        "Chi phí khác",
        "(10)",
        "(10)",
        "Lãi thuần từ hoạt động khác",
        "70",
        "70",
    ]


def _net(owner: str = "5. Lãi thuần từ hoạt động kinh doanh khác") -> list[str]:
    return [
        owner,
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Thu từ các khoản nợ đã xử lý",
        "10",
        "9",
        "Lãi từ các công cụ tài chính phái sinh khác",
        "2",
        "3",
        "Thu nhập/(chi phí) khác",
        "4",
        "5",
        "16",
        "17",
    ]


def test_gross_optional_children_form_one_bank_blind_graph() -> None:
    result = matcher.build_other_activity_variant_graph_document_v1([_page(_gross())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["presentation"].startswith("GROSS_")
    assert result["regions"][0]["layout"]["observed_roles"] == [
        "INCOME_PARENT",
        "INCOME_DERIVATIVE",
        "DEBT_RECOVERY",
        "EXPENSE_PARENT",
        "EXPENSE_DERIVATIVE",
        "EXPENSE_OTHER",
        "NET_TOTAL",
    ]


def test_minimal_gross_parent_and_one_child_per_side_is_sufficient() -> None:
    texts = [
        "29. Lãi thuần từ hoạt động khác",
        "Năm 2025",
        "Năm 2024",
        "Triệu đồng",
        "Thu nhập từ hoạt động khác",
        "100",
        "90",
        "Thu nhập khác",
        "100",
        "90",
        "Chi phí từ hoạt động khác",
        "(30)",
        "(20)",
        "Chi phí khác",
        "(30)",
        "(20)",
        "70",
        "70",
    ]
    result = matcher.build_other_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_roles"] == [
        "INCOME_PARENT",
        "INCOME_OTHER",
        "EXPENSE_PARENT",
        "EXPENSE_OTHER",
    ]


def test_explicit_net_label_can_close_provider_order_without_trailing_numbers() -> None:
    texts = [
        "31. Lãi thuần từ hoạt động khác",
        "Năm 2025",
        "Năm 2024",
        "Triệu đồng",
        "Thu nhập từ hoạt động khác",
        "100",
        "90",
        "Thu từ các công cụ phái sinh khác",
        "100",
        "90",
        "Chi phí từ hoạt động khác",
        "(30)",
        "(20)",
        "Chi từ các công cụ phái sinh khác",
        "(30)",
        "(20)",
        "70",
        "70",
        "Lãi thuần từ hoạt động khác",
    ]
    result = matcher.build_other_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["trailing_numeric_count_after_last_role"] == 0
    assert "NET_TOTAL" in region["layout"]["observed_roles"]


def test_gross_parents_without_any_child_remain_unresolved() -> None:
    texts = [
        "29. Lãi thuần từ hoạt động khác",
        "Năm 2025",
        "Năm 2024",
        "Triệu đồng",
        "Thu nhập từ hoạt động khác",
        "100",
        "90",
        "Chi phí từ hoạt động khác",
        "(30)",
        "(20)",
        "70",
        "70",
    ]
    result = matcher.build_other_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_net_only_variant_does_not_require_gross_parents() -> None:
    result = matcher.build_other_activity_variant_graph_document_v1([_page(_net())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["net_only_variant_region_count"] == 1


def test_q1_variant_is_recorded_without_bank_or_page_rule() -> None:
    texts = _gross()
    texts[1:3] = [
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2026",
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2025",
    ]
    result = matcher.build_other_activity_variant_graph_document_v1([_page(texts)])
    assert result["regions"][0]["layout"]["q1_period_context"] is True


def test_children_before_gross_parent_fail_closed() -> None:
    texts = _gross()
    parent = texts.pop(4)
    texts.insert(13, parent)
    result = matcher.build_other_activity_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_statement_aggregate_without_arabic_detailed_note_is_negative_control() -> None:
    result = matcher.build_other_activity_variant_graph_document_v1(
        [_page(_gross("Lãi thuần từ hoạt động khác"))]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_two_complete_regions_cannot_claim_unique_location() -> None:
    result = matcher.build_other_activity_variant_graph_document_v1(
        [_page(_gross(), 1), _page(_net("30. Lãi thuần từ hoạt động khác"), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_gross())]
    result = matcher.build_other_activity_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "oavgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.OtherActivityVariantGraphV1Error, match="replay exactly"):
        matcher.validate_other_activity_variant_graph_replay_v1(forged, pages)
