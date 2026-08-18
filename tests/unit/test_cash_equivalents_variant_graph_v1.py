from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/cash_equivalents_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("cash_equivalents_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], sequence: int = 1) -> dict[str, object]:
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
    return {"lines": lines, "page_sequence": sequence, "primary_numeric_authority": True}


def _detail(owner: str = "20. Tiền và các khoản tương đương tiền") -> list[str]:
    return [
        owner,
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Tiền mặt và vàng",
        "10.000",
        "9.000",
        "Tiền gửi tại NHNN",
        "20.000",
        "18.000",
        "Tiền gửi không kỳ hạn tại các TCTD khác",
        "30.000",
        "27.000",
        "Tiền gửi có kỳ hạn tại các TCTD khác với kỳ hạn không quá 3 tháng",
        "40.000",
        "36.000",
        "100.000",
        "90.000",
    ]


def test_split_interbank_variant_forms_one_graph() -> None:
    result = matcher.build_cash_equivalents_variant_graph_document_v1([_page(_detail())])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["interbank_presentation"] == ("DEMAND_AND_TERM_SPLIT")


def test_combined_interbank_and_optional_securities_form_same_core() -> None:
    texts = _detail()
    texts[10:16] = [
        "Tiền, ngoại hối gửi tại các TCTD khác với kỳ hạn gốc không quá 3 tháng",
        "70.000",
        "63.000",
        "Chứng khoán có thời hạn thu hồi hoặc đáo hạn không quá 3 tháng",
        "5.000",
        "4.000",
    ]
    result = matcher.build_cash_equivalents_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["securities_row_present"] is True


@pytest.mark.parametrize(
    "central_bank_label",
    [
        "Tiền gửi tại Ngân hàng Trung ương",
        "Tiền gửi tại NHĨNN",
    ],
)
def test_extended_profile_accepts_generic_central_bank_names_and_one_edit_ocr_noise(
    central_bank_label: str,
) -> None:
    texts = _detail()
    texts[7] = central_bank_label
    baseline = matcher.build_cash_equivalents_variant_graph_document_v1([_page(texts)])
    assert baseline["status"] == "UNRESOLVED_NO_UNIQUE_REGION"
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(texts)], variant_profile=matcher.EXTENDED_VARIANT_PROFILE
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert "CENTRAL_BANK_DEPOSIT" in result["regions"][0]["layout"]["observed_roles"]


def test_extended_profile_does_not_fuzz_an_unrelated_deposit_counterparty() -> None:
    texts = _detail()
    texts[7] = "Tiền gửi tại khách hàng"
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(texts)], variant_profile=matcher.EXTENDED_VARIANT_PROFILE
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_extended_profile_joins_a_wrapped_interbank_term_label() -> None:
    texts = _detail()
    texts[13:14] = [
        "Tiền gửi tại các TCTD khác có kỳ hạn không quá",
        "ba tháng",
    ]
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(texts)], variant_profile=matcher.EXTENDED_VARIANT_PROFILE
    )
    assert "INTERBANK_TERM_UP_TO_3_MONTHS" in result["regions"][0]["layout"]["observed_roles"]


def test_extended_profile_joins_wrapped_label_after_two_provider_order_values() -> None:
    texts = _detail()
    texts[13:14] = [
        "Tiền gửi tại các TCTD khác có kỳ hạn",
        "40.000",
        "36.000",
        "không quá ba tháng",
    ]
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(texts)], variant_profile=matcher.EXTENDED_VARIANT_PROFILE
    )
    assert "INTERBANK_TERM_UP_TO_3_MONTHS" in result["regions"][0]["layout"]["observed_roles"]


def test_cash_flow_total_before_components_variant_is_supported() -> None:
    texts = _detail("Tiền và các khoản tương đương tiền gồm có:")
    result = matcher.build_cash_equivalents_variant_graph_document_v1([_page(texts)])
    assert result["regions"][0]["layout"]["presentation"] == ("CASH_FLOW_TOTAL_BEFORE_COMPONENTS")


def test_policy_text_without_axes_and_numbers_is_negative_control() -> None:
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [
            _page(
                [
                    "8. Tiền và các khoản tương đương tiền",
                    "Tiền và các khoản tương đương tiền bao gồm tiền mặt, tiền gửi tại NHNN và tiền gửi tại TCTD khác",
                ]
            )
        ]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_cash_flow_ending_balance_without_components_is_negative_control() -> None:
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(["Tiền và các khoản tương đương tiền cuối kỳ", "100.000", "90.000"])]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_two_complete_regions_cannot_claim_unique_location() -> None:
    result = matcher.build_cash_equivalents_variant_graph_document_v1(
        [_page(_detail(), 1), _page(_detail(), 2)]
    )
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_detail())]
    result = matcher.build_cash_equivalents_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "cevgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.CashEquivalentsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_cash_equivalents_variant_graph_replay_v1(forged, pages)
