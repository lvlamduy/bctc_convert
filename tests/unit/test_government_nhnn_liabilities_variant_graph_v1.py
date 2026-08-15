from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/government_nhnn_liabilities_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location(
    "government_nhnn_liabilities_variant_graph_v1", _PATH
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


def test_aggregate_only_and_rich_variants_are_both_generic_complete_regions() -> None:
    aggregate = matcher.build_government_nhnn_liabilities_variant_graph_document_v1(
        [
            _page(
                [
                    "15",
                    "Các khoản nợ Chính phủ và NHNN",
                    "30/06/2026",
                    "31/12/2025",
                    "Triệu đồng",
                    "Triệu đồng",
                    "Các khoản nợ Chính phủ và NHNN",
                    "100",
                    "90",
                    "100",
                    "90",
                ]
            )
        ]
    )
    rich = matcher.build_government_nhnn_liabilities_variant_graph_document_v1(
        [
            _page(
                [
                    "9. Các khoản nợ Chính phủ và Ngân hàng Nhà nước",
                    "30/06/2026",
                    "31/12/2025",
                    "Triệu VND",
                    "Triệu VND",
                    "Vay Ngân hàng Nhà nước",
                    "10",
                    "9",
                    "Tiền gửi thanh toán của Kho bạc Nhà nước",
                    "20",
                    "18",
                    "Giao dịch bán và mua lại trái phiếu Chính phủ với Kho bạc Nhà nước",
                    "5",
                    "4",
                    "35",
                    "31",
                ]
            )
        ]
    )

    assert aggregate["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert aggregate["regions"][0]["layout"]["presentation"] == (
        "AGGREGATE_ONLY_WITH_REPEATED_FAMILY_ROW"
    )
    assert rich["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert "REPO" in rich["regions"][0]["layout"]["detail_roles"]


def test_document_inherited_unit_variant_does_not_require_local_unit_lines() -> None:
    result = matcher.build_government_nhnn_liabilities_variant_graph_document_v1(
        [
            _page(
                [
                    "7. CÁC KHOẢN NỢ CHÍNH PHỦ VÀ NGÂN HÀNG TRUNG ƯƠNG",
                    "30/06/2026",
                    "31/12/2025",
                    "Vay Ngân hàng Trung ương",
                    "40",
                    "70",
                    "Tiền gửi không kỳ hạn của KBNN",
                    "2",
                    "1",
                    "42",
                    "71",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["unit_scope_requires_document_inheritance"] is True


@pytest.mark.parametrize(
    "texts",
    [
        ["Các khoản nợ Chính phủ và NHNN", "30/06/2026", "31/12/2025", "100", "90"],
        [
            "15 Tăng/(giảm) các khoản nợ Chính phủ và NHNN",
            "30/06/2026",
            "31/12/2025",
            "Vay NHNN",
            "100",
            "90",
        ],
    ],
)
def test_balance_sheet_or_cash_flow_mentions_are_negative_controls(texts: list[str]) -> None:
    result = matcher.build_government_nhnn_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_exact_replay_rejects_coordinated_region_tamper() -> None:
    pages = [
        _page(
            [
                "7",
                "Các khoản nợ Chính phủ và NHNN",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Triệu đồng",
                "Vay NHNN",
                "10",
                "9",
                "Tiền gửi của KBNN",
                "20",
                "18",
                "30",
                "27",
            ]
        )
    ]
    result = matcher.build_government_nhnn_liabilities_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "gnlvv1:result:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(
        matcher.GovernmentNHNNLiabilitiesVariantGraphV1Error, match="replay exactly"
    ):
        matcher.validate_government_nhnn_liabilities_variant_graph_replay_v1(forged, pages)
