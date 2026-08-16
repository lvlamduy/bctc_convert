from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/income_tax_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("income_tax_variant_graph_v1", _PATH)
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


def _tax() -> list[str]:
    return [
        "Chi phí thuế TNDN được ước tính như sau",
        "6 tháng đầu năm 2026",
        "6 tháng đầu năm 2025",
        "Triệu đồng",
        "Lợi nhuận trước thuế TNDN",
        "100",
        "90",
        "Thu nhập không chịu thuế",
        "(5)",
        "(4)",
        "Chi phí không được khấu trừ",
        "2",
        "1",
        "Thu nhập chịu thuế TNDN",
        "97",
        "87",
        "Chi phí thuế TNDN tính trên thu nhập chịu thuế kỳ hiện hành",
        "19",
        "17",
        "Tổng chi phí thuế TNDN hiện hành",
        "19",
        "17",
    ]


def test_current_tax_variant_forms_one_bank_blind_graph() -> None:
    result = matcher.build_income_tax_variant_graph_document_v1([_page(_tax())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_roles"] == [
        "PROFIT_BEFORE_TAX",
        "NON_TAXABLE_INCOME",
        "NON_DEDUCTIBLE_EXPENSE",
        "TAXABLE_INCOME",
        "CURRENT_TAX_AT_RATE",
        "CURRENT_TAX_TOTAL",
    ]


def test_q1_and_optional_adjustments_do_not_change_core_graph() -> None:
    texts = _tax()
    texts[1:3] = [
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2026",
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2025",
    ]
    texts[13:13] = ["Điều chỉnh liên quan đến hợp nhất", "3", "2"]
    result = matcher.build_income_tax_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["q1_period_context"] is True
    assert "CONSOLIDATION_ADJUSTMENT" in result["regions"][0]["layout"]["observed_roles"]


def test_statement_tax_aggregate_without_taxable_income_is_negative_control() -> None:
    texts = [
        "Lợi nhuận trước thuế TNDN",
        "100",
        "90",
        "Chi phí thuế TNDN",
        "20",
        "18",
    ]
    result = matcher.build_income_tax_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_taxable_income_before_profit_fails_closed() -> None:
    texts = _tax()
    block = texts[13:16]
    del texts[13:16]
    texts[4:4] = block
    result = matcher.build_income_tax_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_two_complete_regions_cannot_claim_unique_location() -> None:
    result = matcher.build_income_tax_variant_graph_document_v1(
        [_page(_tax(), 1), _page(_tax(), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_tax())]
    result = matcher.build_income_tax_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "itvgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.IncomeTaxVariantGraphV1Error, match="replay exactly"):
        matcher.validate_income_tax_variant_graph_replay_v1(forged, pages)
