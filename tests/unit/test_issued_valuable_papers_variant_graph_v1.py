from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/issued_valuable_papers_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("issued_valuable_papers_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page_sequence: int = 1) -> dict[str, object]:
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
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


@pytest.mark.parametrize(
    ("texts", "presentation"),
    [
        (
            [
                "20. Phát hành giấy tờ có giá",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Triệu đồng",
                "Trái phiếu",
                "100",
                "90",
                "Từ 12 tháng đến dưới 5 năm",
                "100",
                "90",
                "Chứng chỉ tiền gửi",
                "200",
                "180",
                "Dưới 12 tháng",
                "200",
                "180",
                "300",
                "270",
            ],
            "VARIABLE_INSTRUMENT_TENOR_PERIOD_LAYOUT",
        ),
        (
            [
                "11. Phát hành giấy tờ có giá",
                "30.6.2026",
                "Giá trị ghi sổ",
                "Mệnh giá",
                "Triệu đồng",
                "Triệu đồng",
                "Trái phiếu",
                "100",
                "101",
                "Kỳ hạn 3 năm",
                "100",
                "101",
                "Chứng chỉ tiền gửi",
                "200",
                "200",
                "Kỳ hạn dưới 1 năm",
                "200",
                "200",
                "300",
                "301",
            ],
            "SINGLE_PERIOD_BOOK_VALUE_AND_FACE_VALUE",
        ),
        (
            [
                "10. Phát hành giấy tờ có giá",
                "Đơn vị tính: triệu đồng",
                "Kỳ phiếu",
                "Trái phiếu vô danh",
                "Trái phiếu hữu danh",
                "Chứng chỉ tiền gửi",
                "Dưới 12 tháng",
                "Mệnh giá",
                "1",
                "2",
                "3",
                "4",
                "Từ 12 tháng đến dưới 5 năm",
                "Mệnh giá",
                "5",
                "6",
                "7",
                "8",
            ],
            "TENOR_ROWS_BY_INSTRUMENT_COLUMNS",
        ),
    ],
)
def test_observed_layouts_share_one_generic_graph(texts: list[str], presentation: str) -> None:
    result = matcher.build_issued_valuable_papers_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["presentation"] == presentation
    assert result["regions"][0]["pair_anchor_combinations"]


@pytest.mark.parametrize(
    "texts",
    [
        ["Phát hành giấy tờ có giá", "100", "90"],
        [
            "Tăng/(Giảm) phát hành giấy tờ có giá",
            "30/06/2026",
            "31/12/2025",
            "Trái phiếu",
            "100",
            "90",
        ],
    ],
)
def test_balance_sheet_or_cash_flow_mentions_are_negative_controls(texts: list[str]) -> None:
    result = matcher.build_issued_valuable_papers_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_spelled_out_tenors_are_recognized_without_bank_rules() -> None:
    result = matcher.build_issued_valuable_papers_variant_graph_document_v1(
        [
            _page(
                [
                    "Phát hành giấy tờ có giá",
                    "31.12.2025",
                    "Giá trị ghi sổ",
                    "Mệnh giá",
                    "Triệu VND",
                    "Trái phiếu",
                    "Trái phiếu kỳ hạn từ một năm đến hai năm",
                    "100",
                    "101",
                    "Trái phiếu kỳ hạn ba năm",
                    "200",
                    "201",
                    "Trái phiếu kỳ hạn mười năm",
                    "300",
                    "301",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["tenor_roles"] == [
        "TENOR_LONG",
        "TENOR_MEDIUM_OR_UNSPLIT_OVER_12",
    ]


def test_adjacent_period_continuation_is_one_region() -> None:
    current = _page(
        [
            "Phát hành giấy tờ có giá",
            "31.12.2025",
            "Triệu đồng",
            "Trái phiếu",
            "Kỳ phiếu",
            "Dưới 12 tháng",
            "100",
            "200",
            "Từ 12 tháng đến dưới 5 năm",
            "300",
            "400",
        ],
        1,
    )
    comparative = _page(
        [
            "Phát hành giấy tờ có giá (tiếp theo)",
            "31.12.2024",
            "Triệu đồng",
            "Trái phiếu",
            "Kỳ phiếu",
            "Dưới 12 tháng",
            "90",
            "180",
            "Từ 12 tháng đến dưới 5 năm",
            "280",
            "360",
        ],
        2,
    )
    result = matcher.build_issued_valuable_papers_variant_graph_document_v1([current, comparative])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["complete_region_count"] == 1
    assert result["regions"][0]["page_span"] == [1, 2]
    assert result["regions"][0]["layout"]["presentation"] == ("ADJACENT_PERIOD_TABLE_CONTINUATION")


def test_exact_replay_rejects_coordinated_region_tamper() -> None:
    pages = [
        _page(
            [
                "Phát hành giấy tờ có giá",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Trái phiếu",
                "100",
                "90",
                "Từ 12 tháng đến dưới 5 năm",
                "100",
                "90",
            ]
        )
    ]
    result = matcher.build_issued_valuable_papers_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ivpvgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.IssuedValuablePapersVariantGraphV1Error, match="replay exactly"):
        matcher.validate_issued_valuable_papers_variant_graph_replay_v1(forged, pages)
