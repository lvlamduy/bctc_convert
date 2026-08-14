from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/customer_deposit_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("customer_deposit_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
deposit = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = deposit
_SPEC.loader.exec_module(deposit)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (125 if x < 500 else 100), y + 20],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _row_panel(*, start_y: int = 0, reordered: bool = False) -> list[tuple[str, int, int]]:
    roles = [
        ("Tiền gửi không kỳ hạn", "100", "10"),
        ("Tiền gửi có kỳ hạn", "200", "20"),
        ("Tiền gửi vốn chuyên dùng", "30", None),
        ("Tiền ký quỹ", "40", "4"),
    ]
    if reordered:
        roles = [roles[1], roles[3], roles[0], roles[2]]
    surfaces: list[tuple[str, int, int]] = [
        ("Tiền gửi của khách hàng", 0, start_y),
        ("30/06/2026", 620, start_y + 25),
        ("31/12/2025", 800, start_y + 25),
    ]
    y = start_y + 60
    for label, vnd, foreign in roles:
        surfaces.extend([(label, 0, y), (vnd, 620, y), (vnd, 800, y)])
        if foreign is not None:
            surfaces.extend(
                [
                    ("Bằng VND", 30, y + 24),
                    (vnd, 620, y + 24),
                    (vnd, 800, y + 24),
                    ("Bằng ngoại tệ", 30, y + 48),
                    (foreign, 620, y + 48),
                    (foreign, 800, y + 48),
                ]
            )
            y += 82
        else:
            y += 38
    return surfaces


def test_row_parent_child_graph_preserves_pdf_order_and_boundaries() -> None:
    result = deposit.build_customer_deposit_variant_graph_document_v1(
        [_page(_row_panel(reordered=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["cluster_boundary"] == {
        "first_page_sequence": 1,
        "first_parent_role": "TERM",
        "first_source_line_index": 3,
        "last_page_sequence": 1,
        "last_parent_role": "DEDICATED",
        "last_source_line_index": 30,
    }
    assert region["page_records"][0]["panels"][0]["parent_roles_in_pdf_order"] == [
        "TERM",
        "ESCROW",
        "NO_TERM",
        "DEDICATED",
    ]
    assert region["minimal_anchor"]["combination_size"] == 2
    assert region["layout"]["primary_mode"] == "PARENT_CHILD_ROWS_X_PERIOD_COLUMNS"
    assert len(region["page_records"][0]["children"]) == 6


def test_period_stacked_currency_columns_form_two_complete_panels() -> None:
    surfaces: list[tuple[str, int, int]] = [
        ("Tiền gửi của khách hàng", 0, 0),
        ("Tại ngày 30 tháng 6 năm 2026", 0, 30),
        ("Bằng tiền đồng", 500, 55),
        ("Bằng ngoại tệ", 650, 55),
        ("Tổng cộng", 800, 55),
    ]
    for panel_ordinal, period in enumerate(("30.06.2026", "31.12.2025")):
        base = 90 + panel_ordinal * 210
        surfaces.append((period, 0, base))
        for ordinal, label in enumerate(
            (
                "Tiền gửi không kỳ hạn",
                "Tiền gửi có kỳ hạn",
                "Tiền gửi tiết kiệm không kỳ hạn",
                "Tiền gửi tiết kiệm có kỳ hạn",
                "Tiền ký quỹ",
                "Tiền gửi vốn chuyên dùng",
            )
        ):
            y = base + 28 + ordinal * 28
            surfaces.extend([(label, 0, y), (str(10 + ordinal), 520, y)])

    result = deposit.build_customer_deposit_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["metrics"]["complete_panel_count"] == 2
    assert result["regions"][0]["layout"]["primary_mode"] == (
        "PERIOD_STACKED_ROWS_X_CURRENCY_COLUMNS"
    )
    page = result["regions"][0]["page_records"][0]
    assert [item["axis_role"] for item in page["currency_headers"]] == [
        "VND",
        "FOREIGN",
        "TOTAL",
    ]
    assert len(page["period_headers"]) >= 2


def test_owner_and_all_required_parent_roles_are_both_required() -> None:
    without_owner = _row_panel()[3:]
    result = deposit.build_customer_deposit_variant_graph_document_v1([_page(without_owner)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"

    incomplete = [
        ("Tiền gửi của khách hàng", 0, 0),
        ("Tiền gửi không kỳ hạn", 0, 40),
        ("Tiền gửi có kỳ hạn", 0, 80),
        ("Tiền ký quỹ", 0, 120),
    ]
    result = deposit.build_customer_deposit_variant_graph_document_v1([_page(incomplete)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"

    interbank = [
        ("Tiền gửi và vay các tổ chức tín dụng khác", 0, 0),
        *_row_panel()[3:],
    ]
    result = deposit.build_customer_deposit_variant_graph_document_v1([_page(interbank)])
    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"


def test_exact_replay_rejects_coordinated_boundary_tamper() -> None:
    pages = [_page(_row_panel())]
    result = deposit.build_customer_deposit_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["cluster_boundary"]["last_parent_role"] = "TERM"
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "cdvgv1:region:" + deposit.canonical_json_sha256_v1(
        region_material
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "cdvgv1:result:" + deposit.canonical_json_sha256_v1(result_material)

    with pytest.raises(deposit.CustomerDepositVariantGraphV1Error, match="replay exactly"):
        deposit.validate_customer_deposit_variant_graph_replay_v1(forged, pages)


def test_typed_inputs_and_complete_page_order_fail_closed() -> None:
    poisoned = _page(_row_panel())
    poisoned["primary_numeric_authority"] = 0
    with pytest.raises(deposit.CustomerDepositVariantGraphV1Error, match="exact bool"):
        deposit.build_customer_deposit_variant_graph_document_v1([poisoned])

    skipped = _page(_row_panel(), page_sequence=2)
    with pytest.raises(deposit.CustomerDepositVariantGraphV1Error, match="gap-free"):
        deposit.build_customer_deposit_variant_graph_document_v1([skipped])
