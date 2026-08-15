from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/other_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("other_assets_variant_graph_v1", _PATH)
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
    return {
        "lines": lines,
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


def _axis_and_values() -> list[str]:
    return [
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Triệu đồng",
        "100",
        "90",
        "60",
        "50",
        "40",
        "40",
    ]


def test_split_sibling_notes_are_one_generic_complete_region() -> None:
    result = matcher.build_other_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "13",
                    "Các khoản phải thu",
                    *_axis_and_values(),
                    "Các khoản phải thu nội bộ",
                    "Các khoản phải thu bên ngoài",
                    "Chi phí xây dựng cơ bản, mua sắm TSCĐ",
                    "Ký quỹ, thế chấp, cầm cố",
                    "14",
                    "Tài sản Có khác",
                    "Chi phí chờ phân bổ",
                    "Các khoản khác",
                ]
            )
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["presentation"] == (
        "SPLIT_RECEIVABLE_AND_OTHER_ASSET_SIBLING_NOTES"
    )
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "status": "UNIQUE_FULL_MATCH",
    }


def test_explicit_umbrella_allows_optional_subtables_and_reordered_children() -> None:
    result = matcher.build_other_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "16",
                    "TÀI SẢN CÓ KHÁC",
                    *_axis_and_values(),
                    "Tài sản Có khác",
                    "Vật liệu",
                    "Chi phí trả trước chờ phân bổ",
                    "Các khoản lãi, phí phải thu",
                    "Lãi phải thu từ hoạt động tín dụng",
                    "Các khoản phải thu",
                    "Các khoản phải thu bên ngoài",
                    "Các khoản phải thu nội bộ",
                ]
            )
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["presentation"] == (
        "EXPLICIT_UMBRELLA_WITH_OPTIONAL_CONTINUATION_AND_SUBTABLES"
    )
    assert "RECEIVABLE_INTERNAL" in region["layout"]["detail_roles"]
    assert "MATERIAL" in region["layout"]["detail_roles"]


@pytest.mark.parametrize(
    "texts",
    [
        ["Tài sản Có khác", "30/06/2026", "31/12/2025", "Triệu đồng", "Triệu đồng"],
        [
            "9",
            "Tài sản Có khác",
            "Nợ đủ tiêu chuẩn",
            "Nợ có khả năng mất vốn",
            *_axis_and_values(),
        ],
    ],
)
def test_balance_sheet_or_credit_risk_mentions_are_negative_controls(
    texts: list[str],
) -> None:
    result = matcher.build_other_assets_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_exact_replay_rejects_coordinated_region_tamper() -> None:
    pages = [
        _page(
            [
                "16",
                "Tài sản Có khác",
                *_axis_and_values(),
                "Các khoản phải thu",
                "Các khoản phải thu nội bộ",
                "Các khoản phải thu bên ngoài",
                "Các khoản lãi phí phải thu",
                "Lãi phải thu từ tiền gửi",
            ]
        )
    ]
    result = matcher.build_other_assets_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "oavgv1:result:" + matcher.canonical_json_sha256_v1(material)

    with pytest.raises(matcher.OtherAssetsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_other_assets_variant_graph_replay_v1(forged, pages)
