from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/tangible_fixed_assets_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("leased_fixed_assets_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str]) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [20, index * 30, 500, index * 30 + 20],
                "semantic_text": text,
                "semantic_text_source": "FULL_DOCUMENT_FRESH_VIETOCR_TRANSFORMER",
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": 1,
        "primary_numeric_authority": False,
    }


def _variant(owner: str = "TĂNG, GIẢM TÀI SẢN CỐ ĐỊNH THUÊ TÀI CHÍNH") -> list[str]:
    return [
        owner,
        "Cho kỳ kết thúc ngày 30 tháng 06 năm 2026",
        "Triệu đồng",
        "Nguyên giá",
        "Số dư đầu kỳ",
        "1.000",
        "Tài sản thuê tài chính tăng trong kỳ",
        "100",
        "Tài sản thuê tài chính trả lại trong kỳ",
        "(20)",
        "Số dư cuối kỳ",
        "1.080",
        "Giá trị hao mòn lũy kế",
        "Số dư đầu kỳ",
        "400",
        "Khấu hao trong kỳ",
        "50",
        "Tài sản thuê tài chính trả lại trong kỳ",
        "(10)",
        "Số dư cuối kỳ",
        "440",
    ]


@pytest.mark.parametrize(
    "owner",
    ["TĂNG, GIẢM TÀI SẢN CỐ ĐỊNH THUÊ TÀI CHÍNH", "TSCĐ THUÊ TÀI CHÍNH"],
)
def test_shared_fixed_asset_engine_accepts_leased_owner_variants(owner: str) -> None:
    result = matcher.build_leased_fixed_assets_variant_graph_document_v1([_page(_variant(owner))])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["family_id"] == "LEASED_FIXED_ASSET_MOVEMENT"
    assert result["regions"][0]["layout"]["branch_roles"] == [
        "ACCUMULATED_DEPRECIATION",
        "COST",
    ]
    assert result["regions"][0]["pair_anchor_combinations"] == [
        ["OWNER", "COST"],
        ["OWNER", "ACCUMULATED_DEPRECIATION"],
        ["COST", "ACCUMULATED_DEPRECIATION"],
    ]


def test_generic_finance_lease_policy_and_loan_rows_are_negative_controls() -> None:
    result = matcher.build_leased_fixed_assets_variant_graph_document_v1(
        [
            _page(
                [
                    "Hoạt động cho thuê tài chính",
                    "Cho vay các công ty cho thuê tài chính",
                    "Chính sách tài sản thuê",
                    "Nguyên giá",
                    "Số dư đầu kỳ",
                    "100",
                    "Số dư cuối kỳ",
                    "100",
                    "Hao mòn lũy kế",
                    "Số dư đầu kỳ",
                    "20",
                    "Số dư cuối kỳ",
                    "20",
                ]
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"] == {
        "complete_region_count": 0,
        "near_region_count": 0,
        "owner_candidate_count": 0,
    }


def test_owner_without_both_required_branches_stays_near_only() -> None:
    texts = _variant()
    texts.remove("Giá trị hao mòn lũy kế")
    result = matcher.build_leased_fixed_assets_variant_graph_document_v1([_page(texts)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["near_region_count"] == 1


def test_leased_exact_replay_rejects_coordinated_result_rehash() -> None:
    pages = [_page(_variant())]
    result = matcher.build_leased_fixed_assets_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["branch_order_verified"] = False
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lfavgv1:result:" + matcher.canonical_json_sha256_v1(material)

    with pytest.raises(matcher.TangibleFixedAssetsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_leased_fixed_assets_variant_graph_replay_v1(forged, pages)
