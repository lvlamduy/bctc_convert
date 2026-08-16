from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/interbank_deposits_loans_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("interbank_deposits_loans_variant_graph_v1", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
graph = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = graph
_SPEC.loader.exec_module(graph)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = True,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + (430 if x < 500 else 110), y + 24],
                "source_line_index": index,
                "source_text": text,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _row(
    surfaces: list[tuple[str, int, int]],
    label: str | None,
    current: str,
    comparative: str,
    y: int,
) -> None:
    if label is not None:
        surfaces.append((label, 0, y))
    surfaces.extend([(current, 650, y), (comparative, 820, y)])


def _table(
    *,
    explicit_deposit_parent: bool = True,
    family_total: bool = True,
    reverse_deposit_groups: bool = False,
) -> list[tuple[str, int, int]]:
    surfaces = [
        ("Tiền gửi và cho vay các TCTD khác", 0, 0),
        ("30/06/2026", 650, 28),
        ("31/12/2025", 820, 28),
        ("Triệu đồng", 650, 52),
        ("Triệu đồng", 820, 52),
    ]
    if explicit_deposit_parent:
        surfaces.append(("Tiền gửi tại các TCTD khác", 0, 80))
    groups = [
        (
            "Tiền gửi không kỳ hạn",
            "Bằng VND",
            "60",
            "55",
            "Bằng ngoại tệ",
            "10",
            "8",
        ),
        (
            "Tiền gửi có kỳ hạn",
            "Bằng VND",
            "100",
            "90",
            "Bằng ngoại tệ",
            "20",
            "18",
        ),
    ]
    if reverse_deposit_groups:
        groups.reverse()
    y = 115
    for parent, vnd, vnd_current, vnd_prior, fx, fx_current, fx_prior in groups:
        surfaces.append((parent, 0, y))
        surfaces.append((vnd, 40, y + 30))
        _row(surfaces, None, vnd_current, vnd_prior, y + 30)
        surfaces.append((fx, 40, y + 60))
        _row(surfaces, None, fx_current, fx_prior, y + 60)
        y += 90
    _row(surfaces, None, "190", "171", y)
    y += 35
    surfaces.append(("Cho vay các TCTD khác", 0, y))
    surfaces.append(("Bằng VND", 40, y + 30))
    _row(surfaces, None, "30", "25", y + 30)
    surfaces.append(("Trong đó: chiết khấu, tái chiết khấu", 40, y + 60))
    _row(surfaces, None, "12", "10", y + 60)
    _row(surfaces, None, "30", "25", y + 90)
    if family_total:
        _row(surfaces, None, "220", "196", y + 125)
    surfaces.append(("Chứng khoán kinh doanh", 0, y + 170))
    return surfaces


def test_explicit_parent_layout_retains_first_last_boundary_and_nonadditive_detail() -> None:
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1([_page(_table())])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    by_role = {event["role"]: event for event in region["events"]}
    assert region["cluster_boundary"]["first_item_role"] == ("INTERBANK_DEPOSITS_AND_LOANS_OWNER")
    assert region["cluster_boundary"]["last_item_role"] == "FAMILY_TOTAL"
    assert region["layout"]["orientation"] == "ROW_LABELS_BY_PERIOD_COLUMNS"
    assert region["minimal_anchor"]["combination_size"] == 2
    assert by_role["INTERBANK_DEPOSIT_PARENT"]["value_binding"] == (
        "TRAILING_UNLABELED_DEPOSIT_SUBTOTAL"
    )
    assert by_role["INTERBANK_LOAN"]["value_binding"] == ("TRAILING_UNLABELED_PARENT_SUBTOTAL")
    assert by_role["INTERBANK_LOAN_DISCOUNT_REDISCOUNT"]["role_kind"] == ("NON_ADDITIVE_DETAIL")


def test_owner_direct_layout_moves_unlabeled_subtotal_to_synthetic_deposit_parent() -> None:
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1(
        [_page(_table(explicit_deposit_parent=False))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    by_role = {event["role"]: event for event in region["events"]}
    assert region["layout"]["presentation_mode"] == "OWNER_DIRECT_DEMAND"
    assert by_role["INTERBANK_DEPOSIT_PARENT"]["source_label_present"] is False
    assert by_role["INTERBANK_DEPOSIT_PARENT"]["value_binding"] == (
        "TRAILING_UNLABELED_DEPOSIT_SUBTOTAL"
    )
    assert by_role["TERM_DEPOSIT"]["value_binding"] == "NO_VISIBLE_PARENT_VALUE"
    assert by_role["TERM_DEPOSIT"]["value_proposals"] == []


def test_reverse_deposit_group_order_is_a_shared_family_variant() -> None:
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1(
        [_page(_table(reverse_deposit_groups=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["generic_engine_binding"]["mode_id"] == (
        "EXPLICIT_DEPOSIT_PARENT_TERM_THEN_DEMAND"
    )


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
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["regions"][0]["layout"]["meaningful_axes"]["period_header_count"] == 2


def test_family_without_printed_grand_total_still_ends_at_loan_subtotal() -> None:
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1(
        [_page(_table(family_total=False))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["cluster_boundary"]["last_item_role"] == "INTERBANK_LOAN"
    assert region["layout"]["family_total_present"] is False


def test_gold_currency_and_vay_variant_uses_explicit_document_level_unit() -> None:
    declaration = _page(
        [("Các số liệu được trình bày theo đơn vị triệu VND", 0, 0)],
        page_sequence=1,
    )
    surfaces = [
        ("TIỀN GỬI VÀ VAY CÁC TCTD KHÁC", 0, 0),
        ("30/06/2026", 650, 30),
        ("31/12/2025", 820, 30),
    ]
    _row(surfaces, "Tiền, vàng gửi không kỳ hạn", "250", "240", 70)
    _row(surfaces, "Bằng VND", "210", "190", 105)
    _row(surfaces, "Bằng vàng và ngoại tệ", "40", "50", 140)
    _row(surfaces, "Tiền, vàng gửi có kỳ hạn", "80", "140", 175)
    _row(surfaces, "Bằng VND", "65", "132", 210)
    _row(surfaces, "Bằng vàng và ngoại tệ", "15", "8", 245)
    _row(surfaces, "Vay các TCTD khác", "40", "25", 280)
    _row(surfaces, "Bằng VND", "21", "21", 315)
    _row(surfaces, "Bằng vàng và ngoại tệ", "19", "4", 350)
    _row(surfaces, None, "370", "405", 390)
    surfaces.append(("TIỀN GỬI CỦA KHÁCH HÀNG", 0, 435))

    result = graph.build_interbank_deposits_loans_variant_graph_document_v1(
        [declaration, _page(surfaces, page_sequence=2)]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    region = result["regions"][0]
    assert region["page_sequence"] == 2
    assert region["layout"]["meaningful_axes"]["unit_scope"] == (
        "DOCUMENT_LEVEL_EXPLICIT_INHERITANCE"
    )
    assert region["cluster_boundary"]["last_source_line_index"] < len(surfaces) - 1


def test_balance_sheet_total_and_quality_table_are_negative_controls() -> None:
    surfaces = [
        ("Tiền gửi và cho vay các TCTD khác", 0, 0),
        ("220", 650, 0),
        ("Phân tích chất lượng dư nợ cho vay", 0, 80),
        ("Tiền gửi không kỳ hạn", 0, 110),
        ("Bằng VND", 40, 140),
        ("10", 650, 140),
        ("Tiền gửi có kỳ hạn", 0, 170),
        ("Bằng ngoại tệ", 40, 200),
        ("5", 650, 200),
    ]
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["regions"] == []


def test_exact_replay_and_exact_bool_reject_coordinated_tamper() -> None:
    pages = [_page(_table())]
    result = graph.build_interbank_deposits_loans_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["regions"][0]["layout"]["family_total_present"] = False
    region_material = copy.deepcopy(forged["regions"][0])
    region_material.pop("region_id")
    forged["regions"][0]["region_id"] = "idlgv1:region:" + (
        graph.canonical_json_sha256_v1(region_material)
    )
    result_material = copy.deepcopy(forged)
    result_material.pop("result_id")
    forged["result_id"] = "idlgv1:result:" + graph.canonical_json_sha256_v1(result_material)
    with pytest.raises(graph.InterbankDepositsLoansVariantGraphV1Error, match="replay exactly"):
        graph.validate_interbank_deposits_loans_variant_graph_replay_v1(forged, pages)

    poisoned = _page(_table(), primary_numeric_authority=True)
    poisoned["primary_numeric_authority"] = 1
    with pytest.raises(graph.InterbankDepositsLoansVariantGraphV1Error, match="exact bool"):
        graph.build_interbank_deposits_loans_variant_graph_document_v1([poisoned])
