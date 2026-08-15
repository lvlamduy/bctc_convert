from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/credit_risk_provision_expense_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "credit_risk_provision_expense_variant_graph_v1", _PATH
)
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


def _region(owner: str = "9. Chi phí/(hoàn nhập) dự phòng rủi ro") -> list[str]:
    return [
        owner,
        "Từ 01/01/2026 đến 30/06/2026",
        "Từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
        "Chi phí dự phòng rủi ro cho vay",
        "khách hàng",
        "100",
        "90",
        "Chi phí/(Hoàn nhập) dự phòng mua nợ",
        "2",
        "1",
        "Chi phí/(Hoàn nhập) dự phòng các khoản rủi",
        "ro khác",
        "(3)",
        "(2)",
        "99",
        "89",
    ]


def test_wrapped_optional_rows_form_one_bank_blind_graph() -> None:
    result = matcher.build_credit_risk_provision_expense_variant_graph_document_v1(
        [_page(_region())]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["observed_roles"] == [
        "CUSTOMER_LOAN_PROVISION",
        "PURCHASED_DEBT_PROVISION",
        "OTHER_RISK_PROVISION",
    ]
    assert result["regions"][0]["pair_anchor_combinations"]


def test_q1_variant_is_recorded_without_bank_or_page_rule() -> None:
    texts = _region()
    texts[1:3] = [
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2026",
        "Cho kỳ kế toán 3 tháng kết thúc ngày 31 tháng 3 năm 2025",
    ]
    result = matcher.build_credit_risk_provision_expense_variant_graph_document_v1([_page(texts)])
    assert result["regions"][0]["layout"]["q1_period_context"] is True


def test_statement_aggregate_without_arabic_detailed_note_is_negative_control() -> None:
    result = matcher.build_credit_risk_provision_expense_variant_graph_document_v1(
        [_page(_region("Chi phí dự phòng rủi ro tín dụng"))]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_two_complete_regions_cannot_claim_unique_location() -> None:
    result = matcher.build_credit_risk_provision_expense_variant_graph_document_v1(
        [_page(_region(), 1), _page(_region("10. Chi phí dự phòng rủi ro tín dụng"), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    assert result["metrics"]["complete_region_count"] == 2


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_region())]
    result = matcher.build_credit_risk_provision_expense_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "crpevgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(
        matcher.CreditRiskProvisionExpenseVariantGraphV1Error, match="replay exactly"
    ):
        matcher.validate_credit_risk_provision_expense_variant_graph_replay_v1(forged, pages)
