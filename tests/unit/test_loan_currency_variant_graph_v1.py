from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/loan_currency_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_currency_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
graph = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = graph
_SPEC.loader.exec_module(graph)


def _page(
    texts: list[str], *, page_sequence: int = 1, primary_numeric_authority: bool = True
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [
                    80 if not any(char.isdigit() for char in text) else 700,
                    80 + i * 30,
                    620 if not any(char.isdigit() for char in text) else 850,
                    104 + i * 30,
                ],
                "source_line_index": i,
                "source_text": text,
                "vietocr_text": text,
            }
            for i, text in enumerate(texts)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _implicit_family(*, reverse: bool = False) -> list[str]:
    children = [
        "Bằng đồng Việt Nam",
        "123.456",
        "111.222",
        "Bằng ngoại tệ và vàng",
        "7.890",
        "6.789",
    ]
    if reverse:
        children = children[3:] + children[:3]
    return [
        "5. Cho vay khách hàng",
        "30/06/2026",
        "31/12/2025",
        "Triệu đồng",
        "Triệu đồng",
        *children,
        "333.357",
        "118.011",
        "6. Dự phòng rủi ro cho vay khách hàng",
    ]


@pytest.mark.parametrize("reverse", [False, True])
def test_implicit_branch_and_unordered_children_bind_first_last_boundary(reverse: bool) -> None:
    result = graph.build_loan_currency_variant_graph_document_v1(
        [_page(_implicit_family(reverse=reverse))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["branch_match"] is None
    assert region["minimal_anchor"] == {
        "combination_size": 2,
        "pair_search_exhausted_before_larger_combinations": True,
        "roles": ["LOAN_OWNER", region["events"][0]["role"]],
    }
    assert {event["role"] for event in region["events"]} == {
        "VND_LOANS",
        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
    }
    assert region["cluster_boundary"]["first_source_line_index"] == 0
    assert region["cluster_boundary"]["last_source_line_index"] < len(_implicit_family()) - 1
    assert len(region["layout"]["period_headings"]) == 2
    assert len(region["layout"]["unit_headings"]) == 2


def test_wrapped_explicit_branch_and_two_page_continuation_are_supported() -> None:
    pages = [
        _page(
            [
                "9. CHO VAY KHÁCH HÀNG",
                "Phân tích dư nợ theo loại hình",
                "tiền tệ",
                "30/06/2026",
                "31/12/2025",
                "Bằng VND",
                "500",
                "400",
            ]
        ),
        _page(
            [
                "Bằng vàng và ngoại tệ",
                "50",
                "40",
                "550",
                "440",
            ],
            page_sequence=2,
        ),
    ]
    result = graph.build_loan_currency_variant_graph_document_v1(pages)

    region = result["regions"][0]
    assert region["branch_match"]["surface"] == "Phân tích dư nợ theo loại hình tiền tệ"
    assert region["cluster_boundary"]["last_page_sequence"] == 2


def test_deposit_currency_pair_and_owner_after_pair_are_negative_controls() -> None:
    deposit = _page(
        [
            "Tiền gửi và cho vay các TCTD khác",
            "Tiền gửi không kỳ hạn",
            "Bằng VND",
            "100",
            "90",
            "Bằng ngoại tệ",
            "20",
            "10",
        ]
    )
    result = graph.build_loan_currency_variant_graph_document_v1([deposit])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["metrics"]["orphan_currency_pair_negative_control_count"] == 1

    after = _page(
        [
            "Bằng VND",
            "100",
            "90",
            "Bằng ngoại tệ",
            "20",
            "10",
            "Cho vay khách hàng",
        ]
    )
    result = graph.build_loan_currency_variant_graph_document_v1([after])
    assert result["regions"] == []
    assert result["metrics"]["loan_owner_candidate_count"] == 1


def test_missing_child_is_retained_unresolved_and_multiple_regions_are_ambiguous() -> None:
    missing = _page(["Cho vay khách hàng", "Bằng VND", "100", "90"])
    result = graph.build_loan_currency_variant_graph_document_v1([missing])
    assert result["regions"] == []
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "MISSING_FOREIGN_CURRENCY_AND_GOLD_LOANS_WITH_TWO_PERIOD_VALUES"
    ]

    first = _page(_implicit_family())
    second = _page(_implicit_family(), page_sequence=2)
    result = graph.build_loan_currency_variant_graph_document_v1([first, second])
    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"]["complete_region_count"] == 2


def test_annual_profile_uses_nearest_owner_and_branch_before_table_parent() -> None:
    pages = [
        _page(["9. Cho vay khách hàng"]),
        _page(
            [
                "Phân tích dư nợ cho vay theo loại tiền tệ",
                "Cho vay khách hàng",
                "Bằng VND",
                "500",
                "400",
                "Bằng ngoại tệ",
                "50",
                "40",
                "Dân số tín dụng khác",
                "9",
                "8",
            ],
            page_sequence=2,
        ),
    ]
    result = graph.build_loan_currency_variant_graph_document_v1(
        pages, enable_extended_annual_variants=True
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["owner_context"]["page_sequence"] == 2
    assert region["branch_match"]["surface"] == ("Phân tích dư nợ cho vay theo loại tiền tệ")
    assert region["cluster_boundary"]["first_item_role"] == "OPTIONAL_CURRENCY_BRANCH"
    assert [len(event["value_proposals"]) for event in region["events"]] == [2, 2]
    assert any(
        item["unresolved_reasons"] == ["SHADOWED_EARLIER_OWNER_FOR_SAME_CURRENCY_CLUSTER"]
        for item in result["near_regions"]
    )


def test_annual_profile_stops_at_isolated_next_note_number() -> None:
    pages = [
        _page(["5. Cho vay khách hàng"]),
        _page(
            [
                "6.",
                "Tiền gửi và cho vay các tổ chức tín dụng khác",
                "Cho vay bằng VND",
                "100",
                "90",
                "Cho vay bằng ngoại tệ",
                "20",
                "10",
            ],
            page_sequence=2,
        ),
    ]
    result = graph.build_loan_currency_variant_graph_document_v1(
        pages, enable_extended_annual_variants=True
    )

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []


def test_exact_replay_and_bool_typing_reject_coordinated_tamper() -> None:
    pages = [_page(_implicit_family())]
    result = graph.build_loan_currency_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["orientation"] = "FORGED"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "lcvgv1:region:" + graph.canonical_json_sha256_v1(
        region_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "lcvgv1:result:" + graph.canonical_json_sha256_v1(result_material)
    with pytest.raises(graph.LoanCurrencyVariantGraphV1Error, match="replay exactly"):
        graph.validate_loan_currency_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_implicit_family())
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(graph.LoanCurrencyVariantGraphV1Error, match="exact bool"):
        graph.build_loan_currency_variant_graph_document_v1([poisoned])
