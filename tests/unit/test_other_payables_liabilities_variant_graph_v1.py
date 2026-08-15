from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/other_payables_liabilities_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("other_payables_liabilities_variant_graph_v1", _PATH)
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
    "texts",
    [
        [
            "Các khoản phải trả và công nợ khác",
            "30/06/2026",
            "31/12/2025",
            "Triệu đồng",
            "Các khoản phải trả nội bộ",
            "100",
            "90",
            "Các khoản phải trả bên ngoài",
            "200",
            "180",
            "300",
            "270",
        ],
        [
            "CÁC KHOẢN NỢ KHÁC",
            "Số cuối kỳ",
            "Số đầu kỳ",
            "Triệu VND",
            "Các khoản lãi, phí phải trả",
            "10",
            "9",
            "Các khoản phải trả nội bộ",
            "100",
            "90",
            "Phải trả nhân viên",
            "20",
            "18",
            "Các khoản phải trả cho bên ngoài",
            "200",
            "180",
            "Quỹ khen thưởng, phúc lợi",
            "30",
            "27",
            "360",
            "324",
        ],
    ],
)
def test_observed_layouts_share_one_generic_graph(texts: list[str]) -> None:
    result = matcher.build_other_payables_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    roles = result["regions"][0]["layout"]["child_roles"]
    assert "INTERNAL_PAYABLE" in roles
    assert "EXTERNAL_PAYABLE" in roles
    assert result["regions"][0]["pair_anchor_combinations"]


def test_nested_specific_owner_supersedes_broad_owner() -> None:
    result = matcher.build_other_payables_liabilities_variant_graph_document_v1(
        [
            _page(
                [
                    "Các khoản nợ khác",
                    "Các khoản lãi, phí phải trả",
                    "10",
                    "9",
                    "Các khoản phải trả và công nợ khác",
                    "30/06/2026",
                    "31/12/2025",
                    "Triệu đồng",
                    "Các khoản phải trả nội bộ",
                    "100",
                    "90",
                    "Các khoản phải trả bên ngoài",
                    "200",
                    "180",
                    "300",
                    "270",
                ]
            )
        ]
    )
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["owner"]["source_line_index"] == 4
    assert result["metrics"]["near_region_count"] == 1


@pytest.mark.parametrize(
    "texts",
    [
        ["Các khoản nợ khác", "100", "90"],
        [
            "Các khoản phải trả và công nợ khác",
            "30/06/2026",
            "31/12/2025",
            "Các khoản phải trả nội bộ",
            "100",
            "90",
        ],
    ],
)
def test_owner_or_one_child_alone_is_negative_control(texts: list[str]) -> None:
    result = matcher.build_other_payables_liabilities_variant_graph_document_v1([_page(texts)])
    assert result["status"] == "UNRESOLVED_NO_UNIQUE_REGION"


def test_exact_replay_rejects_coordinated_region_tamper() -> None:
    pages = [
        _page(
            [
                "Các khoản nợ khác",
                "30/06/2026",
                "31/12/2025",
                "Triệu đồng",
                "Các khoản phải trả nội bộ",
                "100",
                "90",
                "Các khoản phải trả bên ngoài",
                "200",
                "180",
                "300",
                "270",
            ]
        )
    ]
    result = matcher.build_other_payables_liabilities_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["owner"]["page_sequence"] = 2
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "oplivgv1:graph:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.OtherPayablesLiabilitiesVariantGraphV1Error, match="replay exactly"):
        matcher.validate_other_payables_liabilities_variant_graph_replay_v1(forged, pages)
