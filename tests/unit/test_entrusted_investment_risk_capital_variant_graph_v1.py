from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/entrusted_investment_risk_capital_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "entrusted_investment_risk_capital_variant_graph_v1", _PATH
)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
    lines = []
    y = 0
    for index, text in enumerate(texts):
        if text.isdigit() and index + 1 < len(texts):
            bbox = [10, y, 40, y + 20]
        elif index > 0 and texts[index - 1].isdigit():
            bbox = [60, y, 700, y + 20]
            y += 25
        else:
            bbox = [60, y, 700, y + 20]
            y += 25
        lines.append(
            {
                "bbox": bbox,
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
        )
    return {"lines": lines, "page_sequence": page_sequence, "primary_numeric_authority": True}


@pytest.mark.parametrize(
    ("owner", "child", "presentation"),
    [
        (
            "Vốn tài trợ ủy thác đầu tw, cho vay TCTD chịu rùi ro",
            "Vốn nhận của tổ chức, cá nhân khác",
            "ORGANIZATION_OR_INDIVIDUAL_AGGREGATE",
        ),
        (
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TỔ CHỨC TÍN DỤNG CHỊU RỦI RO",
            "Vốn nhận tài trợ, ủy thác đầu tư, cho vay bằng VND từ",
            "VND_ODA_OR_OTHER_RECEIVED_SOURCE",
        ),
        (
            "VỐN TÀI TRỢ, ỦY THÁC ĐẦU TƯ, CHO VAY TCTD CHỊU RÙI RO",
            "Vốn nhận ủy thác từ NHNN theo Chương trình cho vay hỗ trợ",
            "NHNN_PROGRAMME_RECEIVED_SOURCE",
        ),
    ],
)
def test_three_observed_variants_share_one_generic_graph(
    owner: str, child: str, presentation: str
) -> None:
    result = matcher.build_entrusted_investment_risk_capital_variant_graph_document_v1(
        [
            _page(
                [
                    "20",
                    owner,
                    "30/06/2026",
                    "31/12/2025",
                    "Triệu đồng",
                    "Triệu đồng",
                    child,
                    "2.000",
                    "3.000",
                    "2.000",
                    "3.000",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["presentation"] == presentation
    assert result["regions"][0]["pair_anchor_combinations"]


def test_unnumbered_owner_and_von_tai_tro_currency_child_are_generic_variants() -> None:
    result = matcher.build_entrusted_investment_risk_capital_variant_graph_document_v1(
        [
            _page(
                [
                    "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
                    "31/12/2025",
                    "31/12/2024",
                    "Triệu đồng",
                    "Triệu đồng",
                    "Vốn tài trợ, ủy thác đầu tư, cho vay bằng VND",
                    "3.912.833",
                    "2.793.453",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["anchor_roles"] == ["OWNER", "VND_RECEIVED_SOURCE"]
    assert result["regions"][0]["layout"]["note_heading_context"] is False


@pytest.mark.parametrize(
    "texts",
    [
        [
            "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
            "30/06/2026",
            "31/12/2025",
            "Triệu đồng",
            "Triệu đồng",
            "100",
            "90",
        ],
        [
            "19 Tăng/(giảm) vốn tài trợ, ủy thác đầu tư, cho vay mà TCTD chịu rủi ro",
            "30/06/2026",
            "31/12/2025",
            "Vốn nhận của tổ chức, cá nhân khác",
            "100",
            "90",
        ],
    ],
)
def test_balance_sheet_or_cash_flow_mentions_are_negative_controls(texts: list[str]) -> None:
    result = matcher.build_entrusted_investment_risk_capital_variant_graph_document_v1(
        [_page(texts)]
    )
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_exact_replay_rejects_coordinated_region_tamper() -> None:
    pages = [
        _page(
            [
                "19",
                "Vốn tài trợ, ủy thác đầu tư, cho vay TCTD chịu rủi ro",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Triệu đồng",
                "Vốn nhận của tổ chức, cá nhân khác",
                "100",
                "90",
                "100",
                "90",
            ]
        )
    ]
    result = matcher.build_entrusted_investment_risk_capital_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "eircvv1:result:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(
        matcher.EntrustedInvestmentRiskCapitalVariantGraphV1Error, match="replay exactly"
    ):
        matcher.validate_entrusted_investment_risk_capital_variant_graph_replay_v1(forged, pages)
