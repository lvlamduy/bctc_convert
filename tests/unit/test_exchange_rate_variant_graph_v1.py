from __future__ import annotations

import copy
import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/exchange_rate_variant_graph_v1.py"
SPEC = importlib.util.spec_from_file_location("exchange_rate_variant_graph_v1_test_target", PATH)
assert SPEC is not None and SPEC.loader is not None
matcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = matcher
SPEC.loader.exec_module(matcher)


def _page(texts: list[str], page: int = 1) -> dict[str, object]:
    lines = []
    row_y = 0
    for index, text in enumerate(texts):
        numeric = re.fullmatch(r"[0-9]+(?:[.,][0-9]+)*", text) is not None
        code = re.fullmatch(r"[A-Za-z]{2,4}", text) is not None or text == "Vàng (*)"
        if code:
            x0, x1 = 100, 170
        elif numeric:
            x0, x1 = (500, 620) if index % 3 == 1 else (800, 920)
        else:
            x0, x1 = 80, 700
        if code:
            row_y += 60
            y = row_y + 200
        elif numeric and index >= 1:
            y = row_y + 200
        else:
            y = index * 30
        lines.append(
            {
                "bbox": [x0, y, x1, y + 24],
                "source_line_index": index,
                "source_text": None,
                "vietocr_text": text,
                "vietocr_text_accentless": matcher._accentless(text),
            }
        )
    return {"lines": lines, "page_sequence": page, "primary_numeric_authority": True}


def _table(*, owner: bool = True, split_dates: bool = False) -> list[str]:
    title = ["Tỷ giá một số loại ngoại tệ so với VND tại thời điểm cuối kỳ"] if owner else []
    dates = (
        ["Ngày 31 tháng 3", "Ngày 31 tháng", "năm 2026", "12 năm 2025"]
        if split_dates
        else ["30/06/2026", "31/12/2025"]
    )
    return [
        *title,
        *dates,
        "VND",
        "VND",
        "USD",
        "26.300,00",
        "26.290,00",
        "EUR",
        "30.074,50",
        "30.945,00",
    ]


def test_pair_first_core_finds_one_unique_table() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1([_page(_table())])
    assert result["uniqueness"] == {"complete_region_count": 1, "status": "UNIQUE_FULL_MATCH"}
    assert [row["code"] for row in result["regions"][0]["rows"]] == ["USD", "EUR"]


def test_split_parallel_date_axes_are_joined_by_geometry() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1(
        [_page(_table(split_dates=True))]
    )
    region = next(item for item in result["regions"] if item["status"] == "COMPLETE")
    assert region["current_period"][0]["year"] == 2026
    assert region["comparative_period"][0]["year"] == 2025


def test_fuzzy_currency_codes_and_gold_are_family_level_variants() -> None:
    texts = _table()
    start = texts.index("USD")
    texts[start : start + 6] = [
        "Upy",
        "162,36",
        "168,46",
        "Vàng (*)",
        "500,00",
        "500,00",
    ]
    result = matcher.build_exchange_rate_variant_graph_document_v1([_page(texts)])
    rows = result["regions"][0]["rows"]
    assert [(row["code"], row["fresh_label_match_status"]) for row in rows] == [
        ("JPY", "UNIQUE_EDIT_DISTANCE_ONE_FRESH_VIETOCR_CODE"),
        ("XAU", "GENERIC_VISIBLE_GOLD_LABEL"),
    ]


def test_currency_risk_table_without_exchange_rate_owner_is_negative_control() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1(
        [_page(["Rủi ro tiền tệ", *_table(owner=False)])]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_owner_and_codes_without_period_axis_are_not_complete() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1(
        [_page(["Tỷ giá một số ngoại tệ tại thời điểm lập báo cáo", "VND", "USD", "1", "2"])]
    )
    assert result["metrics"]["complete_region_count"] == 0


def test_two_complete_regions_are_not_unique() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1(
        [_page(_table(), 1), _page(["đối chứng"], 2), _page(_table(), 3)]
    )
    assert result["uniqueness"] == {
        "complete_region_count": 2,
        "status": "NO_UNIQUE_FULL_MATCH",
    }


def test_typed_metric_tamper_rejects() -> None:
    result = matcher.build_exchange_rate_variant_graph_document_v1([_page(_table())])
    forged = copy.deepcopy(result)
    forged["metrics"]["complete_region_count"] = 1.0
    with pytest.raises(matcher.ExchangeRateVariantGraphV1Error):
        matcher.validate_exchange_rate_variant_graph_document_v1(forged)
