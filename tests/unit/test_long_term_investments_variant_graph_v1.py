from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/long_term_investments_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("long_term_investments_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
matcher = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = matcher
_SPEC.loader.exec_module(matcher)


def _page(texts: list[str], *, page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [20, index * 30, 500, index * 30 + 20],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
            }
            for index, text in enumerate(texts)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": False,
    }


def _variant(*, reorder: bool = False) -> list[str]:
    children = [
        "Các khoản đầu tư vào công ty liên doanh",
        "Đầu tư vào công ty liên kết",
        "Các khoản đầu tư dài hạn khác",
    ]
    if reorder:
        children = [children[2], children[0], children[1]]
    return [
        "GÓP VỐN, ĐẦU TƯ DÀI HẠN",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        *children,
        "100",
        "200",
        "300",
        "Dự phòng giảm giá đầu tư dài hạn",
        "(20)",
        "580",
        "Tài sản cố định hữu hình",
    ]


@pytest.mark.parametrize("reorder", [False, True])
def test_one_generic_graph_accepts_optional_children_in_different_orders(reorder: bool) -> None:
    result = matcher.build_long_term_investments_variant_graph_document_v1(
        [_page(_variant(reorder=reorder))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["page_span"] == [1, 1]
    assert region["pair_anchor_combinations"][0] == ["OWNER", "ASSOCIATE"]
    assert set(region["layout"]["child_roles"]) >= {
        "ASSOCIATE",
        "JOINT_VENTURE",
        "OTHER_LONG_TERM",
        "PROVISION",
    }
    assert result["safety"]["bank_filename_note_or_page_used_as_matching_or_routing"] is False


def test_narrative_and_next_family_are_not_accepted_as_the_table() -> None:
    result = matcher.build_long_term_investments_variant_graph_document_v1(
        [
            _page(
                [
                    "Góp vốn, đầu tư dài hạn được ghi nhận theo giá gốc",
                    "Các khoản đầu tư vào công ty liên kết được trích lập dự phòng",
                    "Tài sản cố định hữu hình",
                    "30/06/2026",
                    "31/12/2025",
                    "100",
                    "200",
                    "300",
                ]
            )
        ]
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["complete_region_count"] == 0


def test_exact_replay_and_exact_types_fail_closed() -> None:
    pages = [_page(_variant())]
    result = matcher.build_long_term_investments_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["period_axis_line_count"] = 99
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ltivgv1:result:" + matcher.canonical_json_sha256_v1(material)
    with pytest.raises(matcher.LongTermInvestmentsVariantGraphV1Error, match="replay exactly"):
        matcher.validate_long_term_investments_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_variant())
    poisoned["primary_numeric_authority"] = 0
    with pytest.raises(matcher.LongTermInvestmentsVariantGraphV1Error, match="exact bool"):
        matcher.build_long_term_investments_variant_graph_document_v1([poisoned])
