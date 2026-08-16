from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/central_bank_deposits_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("central_bank_deposits_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
central = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = central
_SPEC.loader.exec_module(central)


def _page(surfaces: list[tuple[str, int, int]], *, page_sequence: int = 1) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (360 if x < 500 else 130), y + 24],
                "source_line_index": index,
                "source_text": text,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


def _table(
    *,
    child_order: tuple[str, str] = ("Bằng VND", "Bằng ngoại tệ"),
    geography: bool = True,
) -> list[tuple[str, int, int]]:
    surfaces = [
        ("Tiền gửi tại NHNN", 0, 0),
        ("30/06/2026", 620, 35),
        ("31/12/2025", 810, 35),
        ("Triệu đồng", 620, 65),
        ("Triệu đồng", 810, 65),
        ("Tiền gửi tại Ngân hàng Nhà nước Việt Nam", 0, 105),
        ("25.269.011", 620, 105),
        ("22.000.000", 810, 105),
    ]
    values = {
        "Bằng VND": ("20.274.233", "18.000.000"),
        "Bằng ngoại tệ": ("4.994.778", "4.000.000"),
    }
    y = 140
    for label in child_order:
        current, comparative = values[label]
        surfaces.extend([(label, 0, y), (current, 620, y), (comparative, 810, y)])
        y += 35
    if geography:
        surfaces.extend(
            [
                ("Tiền gửi tại Ngân hàng Nhà nước Lào", 0, y),
                ("934.855", 620, y),
                ("800.000", 810, y),
                ("Tiền gửi tại Ngân hàng Quốc gia Campuchia", 0, y + 35),
                ("1.213.504", 620, y + 35),
                ("1.000.000", 810, y + 35),
            ]
        )
        y += 70
    surfaces.extend(
        [
            ("27.417.370", 620, y + 10),
            ("23.800.000", 810, y + 10),
            ("Tỷ lệ dự trữ bắt buộc", 0, y + 55),
            ("3%", 620, y + 55),
            ("Tiền gửi và cho vay các TCTD khác", 0, y + 95),
        ]
    )
    return surfaces


def test_parent_children_optional_geography_and_total_form_one_bounded_graph() -> None:
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(_table())])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert [event["role"] for event in region["events"]] == [
        "CENTRAL_BANK_VIETNAM_PARENT",
        "DEPOSIT_VND",
        "DEPOSIT_FOREIGN_CURRENCY",
        "CENTRAL_BANK_LAOS",
        "CENTRAL_BANK_CAMBODIA",
        "TOTAL",
    ]
    assert region["cluster_boundary"]["first_source_line_index"] == 0
    assert region["cluster_boundary"]["last_source_line_index"] == 21
    assert region["layout"]["orientation"] == "ROW_LABELS_BY_PERIOD_COLUMNS"
    assert region["layout"]["meaningful_axes"]["period_header_count"] == 2
    assert region["layout"]["meaningful_axes"]["unit_header_count"] == 2
    assert region["minimal_anchor"]["combination_size"] == 2
    assert region["optional_child_roles"] == [
        "CENTRAL_BANK_LAOS",
        "CENTRAL_BANK_CAMBODIA",
    ]


def test_child_order_is_one_family_variant_and_not_bank_routing() -> None:
    result = central.build_central_bank_deposits_variant_graph_document_v1(
        [_page(_table(child_order=("Bằng ngoại tệ", "Bằng VND"), geography=False))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert (
        result["regions"][0]["generic_engine_binding"]["order_variant"]
        == "FOREIGN_CURRENCY_THEN_VND"
    )
    assert result["regions"][0]["layout"]["variant"] == "VIETNAM_VND_FOREIGN_ONLY"


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
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["meaningful_axes"]["period_header_count"] == 2


def test_end_start_year_headers_and_one_confusable_numeric_glyph_are_structural_only() -> None:
    surfaces = [
        (
            "Số cuối năm"
            if text == "30/06/2026"
            else "Số đầu năm"
            if text == "31/12/2025"
            else "B.416.558"
            if text == "4.994.778"
            else "Bằng Đồng Việt Nam"
            if text == "Bằng VND"
            else text,
            x,
            y,
        )
        for text, x, y in _table(geography=False)
    ]
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    foreign = next(
        event
        for event in result["regions"][0]["events"]
        if event["role"] == "DEPOSIT_FOREIGN_CURRENCY"
    )
    assert foreign["value_proposals"][0]["vietocr_text"] == "B.416.558"
    assert result["regions"][0]["primary_numeric_authority"] is True


def test_geography_only_variant_is_not_forced_into_currency_children() -> None:
    surfaces = [
        ("Tiền gửi tại Ngân hàng Nhà nước", 0, 0),
        ("31/12/2025", 620, 35),
        ("31/12/2024", 810, 35),
        ("Triệu đồng", 620, 65),
        ("Triệu đồng", 810, 65),
        ("Tiền gửi tại Ngân hàng Nhà nước Việt Nam", 0, 105),
        ("37.212.251", 620, 105),
        ("49.081.534", 810, 105),
        ("Tiền gửi tại Ngân hàng Nhà nước Lào", 0, 140),
        ("233.253", 620, 140),
        ("258.959", 810, 140),
        ("37.445.504", 620, 185),
        ("49.340.493", 810, 185),
        ("Tỷ lệ dự trữ bắt buộc", 0, 225),
    ]
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["layout"]["variant"] == "CENTRAL_BANK_GEOGRAPHY_ONLY"
    assert [event["role"] for event in region["events"]] == [
        "CENTRAL_BANK_VIETNAM_PARENT",
        "CENTRAL_BANK_LAOS",
        "TOTAL",
    ]


def test_balance_sheet_total_or_reserve_ratio_table_is_not_a_complete_note() -> None:
    surfaces = [
        ("Tiền gửi tại Ngân hàng Nhà nước", 0, 0),
        ("10.000", 620, 0),
        ("Tỷ lệ dự trữ bắt buộc", 0, 100),
        ("Tiền gửi tại NHNN", 0, 135),
        ("Bằng VND", 0, 170),
        ("3%", 620, 170),
        ("Bằng ngoại tệ", 0, 205),
        ("8%", 620, 205),
    ]
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []


def test_missing_period_unit_or_trailing_total_fails_closed() -> None:
    surfaces = [
        ("Tiền gửi tại NHNN", 0, 0),
        ("Tiền gửi tại Ngân hàng Nhà nước Việt Nam", 0, 45),
        ("Bằng VND", 0, 80),
        ("10", 620, 80),
        ("8", 810, 80),
        ("Bằng ngoại tệ", 0, 115),
        ("2", 620, 115),
        ("1", 810, 115),
    ]
    result = central.build_central_bank_deposits_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    reasons = {reason for item in result["near_regions"] for reason in item["reasons"]}
    assert {"FEWER_THAN_TWO_PERIOD_AXES", "NO_MONETARY_UNIT_AXIS"} <= reasons


def test_exact_replay_and_exact_bool_reject_coordinated_tamper() -> None:
    pages = [_page(_table())]
    result = central.build_central_bank_deposits_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["cluster_boundary"]["last_item_role"] = "CENTRAL_BANK_CAMBODIA"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "cbdvgv1:region:" + central.canonical_json_sha256_v1(
        region_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "cbdvgv1:result:" + central.canonical_json_sha256_v1(result_material)
    with pytest.raises(central.CentralBankDepositsVariantGraphV1Error, match="replay exactly"):
        central.validate_central_bank_deposits_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_table())
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(central.CentralBankDepositsVariantGraphV1Error, match="exact bool"):
        central.build_central_bank_deposits_variant_graph_document_v1([poisoned])
