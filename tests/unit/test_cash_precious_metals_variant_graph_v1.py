from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/cash_precious_metals_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("cash_precious_metals_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
cash = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = cash
_SPEC.loader.exec_module(cash)


def _page(surfaces: list[tuple[str, int, int]], *, page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (300 if x < 500 else 120), y + 24],
                "source_line_index": index,
                "source_text": text,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


def _table(*, owner: str = "Tiền mặt, vàng bạc, đá quý") -> list[tuple[str, int, int]]:
    return [
        (owner, 0, 0),
        ("30/06/2026", 620, 35),
        ("31/12/2025", 800, 35),
        ("Triệu đồng", 620, 65),
        ("Triệu đồng", 800, 65),
        ("Tiền mặt bằng VND", 0, 105),
        ("10", 620, 105),
        ("8", 800, 105),
        ("Tiền mặt bằng ngoại tệ", 0, 140),
        ("20", 620, 140),
        ("9", 800, 140),
        ("Vàng", 0, 175),
        ("1", 620, 175),
        ("2", 800, 175),
        ("31", 620, 215),
        ("19", 800, 215),
        ("Tiền gửi tại NHNN", 0, 270),
    ]


def test_short_owner_required_children_optional_gold_and_total_form_unique_graph() -> None:
    result = cash.build_cash_precious_metals_variant_graph_document_v1([_page(_table())])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert [event["role"] for event in region["events"]] == [
        "CASH_VND",
        "CASH_FOREIGN",
        "MONETARY_GOLD",
        "TOTAL",
    ]
    assert region["cluster_boundary"]["first_source_line_index"] == 0
    assert region["cluster_boundary"]["last_source_line_index"] == 15
    assert region["layout"]["meaningful_axes"]["period_header_count"] == 2
    assert region["layout"]["meaningful_axes"]["unit_header_count"] == 2
    assert region["minimal_anchor"]["combination_size"] == 2


def test_vib_short_gold_owner_and_one_word_gold_are_generic_variants() -> None:
    result = cash.build_cash_precious_metals_variant_graph_document_v1(
        [_page(_table(owner="TIỀN MẶT, VÀNG"))]
    )

    assert result["regions"][0]["layout"]["variant"] == "VND_FOREIGN_AND_MONETARY_GOLD"


def test_annual_2025_and_2024_period_headers_use_the_same_generic_graph() -> None:
    surfaces = [
        (
            "31/12/2025"
            if text == "30/06/2026"
            else "31/12/2024"
            if text == "31/12/2025"
            else text,
            x,
            y,
        )
        for text, x, y in _table()
    ]
    result = cash.build_cash_precious_metals_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["meaningful_axes"]["period_header_count"] == 2


def test_balance_sheet_cashflow_and_risk_surfaces_are_not_complete_notes() -> None:
    surfaces = [
        ("Tiền mặt, vàng bạc, đá quý", 0, 0),
        ("10", 620, 0),
        ("Tiền và các khoản tương đương tiền gồm có:", 0, 100),
        ("Tiền mặt, vàng bạc, đá quý", 0, 135),
        ("20", 620, 135),
        ("Phân loại tài sản tài chính và công nợ tài chính", 0, 220),
        ("Tiền mặt, vàng", 0, 260),
    ]
    result = cash.build_cash_precious_metals_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    reasons = {reason for region in result["near_regions"] for reason in region["reasons"]}
    assert "DISTINCT_CASH_EQUIVALENTS_OR_CASH_FLOW_FAMILY" in reasons
    assert "DISTINCT_FINANCIAL_INSTRUMENT_CLASSIFICATION_FAMILY" in reasons


def test_missing_period_unit_or_total_fails_closed() -> None:
    surfaces = [
        ("Tiền mặt, vàng", 0, 0),
        ("Tiền mặt bằng VND", 0, 50),
        ("10", 620, 50),
        ("8", 800, 50),
        ("Tiền mặt bằng ngoại tệ", 0, 90),
        ("20", 620, 90),
        ("9", 800, 90),
    ]
    result = cash.build_cash_precious_metals_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert any("NO_TWO_AXIS_TRAILING_TOTAL" in item["reasons"] for item in result["near_regions"])


def test_exact_replay_and_typed_page_axis_reject_tamper() -> None:
    pages = [_page(_table())]
    result = cash.build_cash_precious_metals_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["cluster_boundary"]["last_item_role"] = "MONETARY_GOLD"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "cpmvgv1:region:" + cash.canonical_json_sha256_v1(
        region_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "cpmvgv1:result:" + cash.canonical_json_sha256_v1(result_material)
    with pytest.raises(cash.CashPreciousMetalsVariantGraphV1Error, match="replay exactly"):
        cash.validate_cash_precious_metals_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_table())
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(cash.CashPreciousMetalsVariantGraphV1Error, match="exact bool"):
        cash.build_cash_precious_metals_variant_graph_document_v1([poisoned])
