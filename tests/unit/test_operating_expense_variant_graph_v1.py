from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/operating_expense_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("operating_expense_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], sequence: int = 1) -> dict[str, object]:
    lines = []
    for index, text in enumerate(texts):
        numeric = text.replace(".", "").replace(",", "").isdigit()
        x0 = 650 if numeric else 50
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


def _region(owner: str = "19. Chi phí hoạt động") -> list[str]:
    return [
        owner,
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Chi phí cho nhân viên",
        "100",
        "90",
        "Chi lương và phụ cấp",
        "80",
        "70",
        "Chi về tài sản",
        "40",
        "30",
        "Trong đó: Khấu hao tài sản cố định",
        "20",
        "10",
        "Chi nộp thuế và các khoản phí, lệ phí",
        "5",
        "4",
        "145",
        "124",
    ]


def test_optional_context_bound_children_and_reordered_parent_are_unique() -> None:
    result = matcher.build_operating_expense_variant_graph_document_v1([_page(_region())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["top_level_roles"] == ["EMPLOYEE", "ASSET", "TAX_AND_FEES"]
    assert region["layout"]["contextual_child_roles"] == [
        "SALARY_AND_ALLOWANCE",
        "DEPRECIATION",
    ]
    assert region["pair_anchor_combinations"]


def test_q1_header_variant_is_recorded_without_bank_rule() -> None:
    texts = _region()
    texts[1:3] = [
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2026",
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2025",
    ]
    result = matcher.build_operating_expense_variant_graph_document_v1([_page(texts)])
    assert result["regions"][0]["layout"]["q1_period_context"] is True


def test_statement_aggregate_without_arabic_note_is_negative_control() -> None:
    result = matcher.build_operating_expense_variant_graph_document_v1(
        [_page(_region("Chi phí hoạt động"))]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_two_complete_regions_do_not_claim_uniqueness() -> None:
    result = matcher.build_operating_expense_variant_graph_document_v1(
        [_page(_region(), 1), _page(_region("20. Chi phí quản lý chung"), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_exact_replay_rejects_coordinated_tamper() -> None:
    pages = [_page(_region())]
    result = matcher.build_operating_expense_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "oevgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.OperatingExpenseVariantGraphV1Error, match="replay exactly"):
        matcher.validate_operating_expense_variant_graph_replay_v1(forged, pages)
