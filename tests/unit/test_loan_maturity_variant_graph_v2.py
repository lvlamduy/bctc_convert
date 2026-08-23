from __future__ import annotations

import copy
import importlib.util
import inspect
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_maturity_variant_graph_v2.py"
_SPEC = importlib.util.spec_from_file_location("loan_maturity_variant_graph_v2", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
maturity = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = maturity
_SPEC.loader.exec_module(maturity)

_LABELS = {
    "SHORT_TERM": "Nợ ngắn hạn",
    "MEDIUM_TERM": "Nợ trung hạn",
    "LONG_TERM": "Nợ dài hạn",
}
_MONEY = {
    "SHORT_TERM": (10, 11),
    "MEDIUM_TERM": (20, 21),
    "LONG_TERM": (30, 31),
}
_PERCENT = {
    "SHORT_TERM": ("40,00", "41,00"),
    "MEDIUM_TERM": ("20,00", "20,00"),
    "LONG_TERM": ("40,00", "39,00"),
}
_SAME = object()


def _record(
    text: str,
    x: int,
    y: int,
    *,
    height: int = 30,
    source: str | None | object = _SAME,
    width: int = 150,
) -> dict[str, Any]:
    return {
        "bbox": [x, y, x + width, y + height],
        "source_text": text if source is _SAME else source,
        "vietocr_text": text,
    }


def _page(
    records: Sequence[Mapping[str, Any]],
    *,
    page_sequence: int = 1,
) -> dict[str, Any]:
    return {
        "lines": [
            {**copy.deepcopy(record), "source_line_index": index}
            for index, record in enumerate(records)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": True,
    }


def _ordinary_records(
    *,
    branch: str = "Phân tích dư nợ theo thời gian",
    four_lanes: bool = False,
    visual_roles: Sequence[str] = tuple(_LABELS),
    semantic_dates: tuple[str, str] = ("30/06/2026", "31/12/2025"),
    source_dates: tuple[str, str] | None = None,
) -> list[dict[str, Any]]:
    result = [
        _record("5. Cho vay khách hàng", 40, 20, width=300),
        _record(branch, 70, 55, width=470),
        _record(
            semantic_dates[0],
            500 if four_lanes else 550,
            90,
            source=(source_dates or semantic_dates)[0],
            width=120,
        ),
        _record(
            semantic_dates[1],
            800 if four_lanes else 850,
            90,
            source=(source_dates or semantic_dates)[1],
            width=120,
        ),
    ]
    if four_lanes:
        result.extend(
            [
                _record("Triệu đồng", 500, 125, width=110),
                _record("%", 650, 125, width=50),
                _record("Triệu đồng", 800, 125, width=110),
                _record("%", 950, 125, width=50),
            ]
        )
    else:
        result.extend(
            [
                _record("Triệu đồng", 550, 125, width=120),
                _record("Triệu đồng", 850, 125, width=120),
            ]
        )
    for y, role in zip((175, 220, 265), visual_roles, strict=True):
        result.append(_record(_LABELS[role], 100, y, width=310))
        if four_lanes:
            values = (
                str(_MONEY[role][0]),
                _PERCENT[role][0],
                str(_MONEY[role][1]),
                _PERCENT[role][1],
            )
            for surface, x in zip(values, (500, 650, 800, 950), strict=True):
                result.append(_record(surface, x, y - 3, width=100))
        else:
            for surface, x in zip(_MONEY[role], (550, 850), strict=True):
                result.append(_record(str(surface), x, y - 3, width=120))
    if four_lanes:
        for surface, x in zip(
            ("60", "100,00", "63", "100,00"),
            (500, 650, 800, 950),
            strict=True,
        ):
            result.append(_record(surface, x, 310, width=100))
    else:
        result.extend([_record("60", 550, 310, width=120), _record("63", 850, 310, width=120)])
    result.append(_record("Phân tích chất lượng nợ cho vay", 70, 365, width=450))
    return result


def _graph(result: Mapping[str, Any]) -> Mapping[str, Any]:
    assert len(result["graphs"]) == 1
    return result["graphs"][0]


def test_two_money_lanes_are_unique_and_replay_exactly() -> None:
    pages = [_page(_ordinary_records())]
    result = maturity.build_loan_maturity_variant_graph_document_v2(pages)

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = _graph(result)
    assert [row["role"] for row in graph["rows"]] == list(_LABELS)
    assert graph["accounting"]["core_money_values"] == [60, 63]
    assert graph["accounting"]["variant"] == "CORE_TOTAL_ONLY"
    assert graph["period_axis"]["mode"] == "LOCAL_EXACT_DATES"
    assert result["uniqueness"] == {
        "complete_region_count": 1,
        "minimal_role_combination_proved": True,
    }
    assert maturity.validate_loan_maturity_variant_graph_document_v2(result) == result
    assert maturity.validate_loan_maturity_variant_graph_replay_v2(result, pages) == result

    cached = maturity.build_loan_maturity_variant_graph_from_topology_scan_v2(
        pages, result["region_scan"]
    )
    assert cached == result


def test_nearest_core_total_stops_before_next_theo_sibling_with_same_vector() -> None:
    records = _ordinary_records()
    records[-1] = _record("Theo loại tiền tệ", 70, 365, width=450)
    records.extend(
        [
            _record("30/06/2026", 550, 410, width=120),
            _record("31/12/2025", 850, 410, width=120),
            _record("Tiền đồng", 100, 455, width=250),
            _record("60", 550, 452, width=120),
            _record("63", 850, 452, width=120),
        ]
    )

    result = maturity.build_loan_maturity_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = _graph(result)
    assert len(graph["accounting"]["core_total_rows"]) == 1
    assert graph["accounting"]["core_total_rows"][0]["source_line_indices"] == [15, 16]


def test_structural_graph_emits_family_roles_without_report_norm_ids() -> None:
    result = maturity.build_loan_maturity_variant_graph_document_v2([_page(_ordinary_records())])

    assert "report_norm_id" not in repr(result).lower()
    assert tuple(
        inspect.signature(maturity.build_loan_maturity_variant_graph_document_v2).parameters
    ) == ("document_pages",)
    assert "bctc_ai.mapping" not in _MODULE_PATH.read_text()


def test_reordered_children_are_bound_visually_then_emitted_in_schema_order() -> None:
    result = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_ordinary_records(visual_roles=("LONG_TERM", "SHORT_TERM", "MEDIUM_TERM")))]
    )

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    rows = _graph(result)["rows"]
    assert [row["role"] for row in rows] == list(_LABELS)
    assert [[cell["surface"] for cell in row["values"]] for row in rows] == [
        ["10", "11"],
        ["20", "21"],
        ["30", "31"],
    ]


def test_four_lanes_keep_108_style_child_percent_and_printed_100_percent_total() -> None:
    result = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_ordinary_records(four_lanes=True))]
    )

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = _graph(result)
    assert graph["unit_scope"]["lane_types"] == [
        "MONEY",
        "PERCENT",
        "MONEY",
        "PERCENT",
    ]
    assert result["metrics"]["percentage_child_cell_count"] == 6
    assert result["metrics"]["source_total_percentage_corroboration_cell_count"] == 2
    assert len(graph["accounting"]["percentage_total_rows"]) == 1


def test_optional_intermediate_margin_and_grand_total_are_separate_from_752_core() -> None:
    records = _ordinary_records()
    reset = records.pop()
    records.insert(6, _record("Dư nợ cho vay", 90, 150, width=260))
    for record in records[7:]:
        record["bbox"][1] += 25
        record["bbox"][3] += 25
    records.extend(
        [
            _record(
                "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
                100,
                360,
                width=650,
            ),
            _record("5", 550, 357, width=120),
            _record("7", 850, 357, width=120),
            _record("65", 550, 405, width=120),
            _record("70", 850, 405, width=120),
            {**reset, "bbox": [70, 455, 520, 485]},
        ]
    )

    result = maturity.build_loan_maturity_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = _graph(result)
    assert "report_norm_id_candidate" not in graph["margin"]
    assert [cell["surface"] for cell in graph["margin"]["values"]] == ["5", "7"]
    assert graph["accounting"]["core_money_values"] == [60, 63]
    assert graph["accounting"]["grand_money_values"] == [65, 70]
    assert graph["accounting"]["variant"] == "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"


def _additional_population_records(*, current_surface: str | None) -> list[dict[str, Any]]:
    records = _ordinary_records()
    reset = records.pop()
    parent_values = []
    child_values = []
    if current_surface is not None:
        parent_values.append(_record(current_surface, 550, 347, width=120))
        child_values.append(_record(current_surface, 550, 407, width=120))
    parent_values.append(_record("5", 850, 347, width=120))
    child_values.append(_record("5", 850, 407, width=120))
    records.extend(
        [
            _record("Nghiệp vụ phát hành thư tín dụng trả chậm", 100, 345, width=440),
            *parent_values,
            _record("phát sinh trước ngày 01 tháng 7 năm 2024", 100, 375, width=430),
            _record("Nợ ngắn hạn", 100, 405, width=280),
            *child_values,
            _record("65" if current_surface is not None else "60", 550, 450, width=120),
            _record("68", 850, 450, width=120),
            {**reset, "bbox": [70, 510, 520, 540]},
            _record("22", 700, 570, width=40),
        ]
    )
    return records


def test_additional_source_population_requires_observed_parent_child_and_grand_equations() -> None:
    visible = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_additional_population_records(current_surface="5"))]
    )
    assert visible["status"] == "ACCEPTED_VARIANT_GRAPH"
    graph = _graph(visible)
    assert graph["accounting"]["variant"] == ("LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL")
    assert [
        check["status"] for check in graph["accounting"]["additional_source_population_checks"]
    ] == [
        "EXACT",
        "EXACT",
        "EXACT",
        "EXACT",
    ]
    assert [cell["surface"] for cell in graph["additional_source_populations"][0]["values"]] == [
        "5",
        "5",
    ]

    detector_omitted = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_additional_population_records(current_surface=None))]
    )
    missing_graph = _graph(detector_omitted)
    assert detector_omitted["status"] == "UNRESOLVED"
    assert missing_graph["unresolved_reasons"] == [
        "ADDITIONAL_POPULATION_VISIBLE_DASH_EVIDENCE_REQUIRED"
    ]
    assert missing_graph["additional_source_populations"][0]["grand_total"][
        "source_line_indices"
    ] != [len(_additional_population_records(current_surface=None)) - 1]
    assert [cell["status"] for cell in missing_graph["additional_source_populations"][0]["values"]][
        0
    ] == "MISSING_DETECTOR_CELL_REQUIRES_AUTHENTICATED_PIXEL_EVIDENCE"


@pytest.mark.parametrize(
    ("branch", "variant"),
    [
        ("Theo kỳ hạn", "TENOR_WORDING"),
        (
            "Phân tích dư nợ cho vay theo thời hạn gốc của khoản vay",
            "ORIGINAL_TERM_WORDING",
        ),
        ("Phân tích dư nợ theo thời gian đáo hạn", "MATURITY_TIME_WORDING"),
    ],
)
def test_branch_wording_variants_share_the_same_graph(branch: str, variant: str) -> None:
    result = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_ordinary_records(branch=branch))]
    )

    assert result["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert _graph(result)["branch"]["variant"] == variant


def test_unambiguous_mdy_and_bound_pp_impossible_date_correction_are_typed_modes() -> None:
    mdy = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_ordinary_records(semantic_dates=("09/30/2025", "12/31/2024")))]
    )
    assert _graph(mdy)["period_axis"]["mode"] == "LOCAL_UNAMBIGUOUS_MONTH_DAY_YEAR"

    corrected = maturity.build_loan_maturity_variant_graph_document_v2(
        [
            _page(
                _ordinary_records(
                    semantic_dates=("30/06/2026", "51/12/2025"),
                    source_dates=("30/06/2026", "31/12/2025"),
                )
            )
        ]
    )
    assert _graph(corrected)["period_axis"]["mode"] == ("BOUND_SOURCE_EXACT_DATE_CHALLENGER")
    corrected_raw = _graph(corrected)["period_axis"]["raw_date_evidence"]
    conflict = next(
        item for item in corrected_raw if item["vietocr_transformer_surface"] == "51/12/2025"
    )
    assert conflict["ppocrv6_surface"] == "31/12/2025"
    assert conflict["selected_normalized_period"] == "31/12/2025"
    assert conflict["selection_mode"] == "BOUND_PPOCRV6_IMPOSSIBLE_DATE_CHALLENGER"


def test_year_end_relative_headers_are_refined_without_collapsing_ordinary_roles() -> None:
    year_end = maturity.build_loan_maturity_variant_graph_document_v2(
        [
            _page(
                _ordinary_records(
                    semantic_dates=("Số cuối năm", "Số đầu năm (Trình bày lại)"),
                )
            )
        ]
    )
    ordinary = maturity.build_loan_maturity_variant_graph_document_v2(
        [_page(_ordinary_records(semantic_dates=("Số cuối kỳ", "Số đầu kỳ")))]
    )

    year_end_axis = _graph(year_end)["period_axis"]
    assert year_end["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert year_end_axis["mode"] == "LOCAL_RELATIVE_YEAR_END_ROLES"
    assert [
        (item["source_line_index"], item["vietocr_transformer_surface"])
        for item in year_end_axis["raw_date_evidence"]
    ] == [(2, "Số cuối năm"), (3, "Số đầu năm (Trình bày lại)")]
    assert {item["selection_mode"] for item in year_end_axis["raw_date_evidence"]} == {
        "VIETOCR_RELATIVE_YEAR_END_ROLE"
    }

    ordinary_axis = _graph(ordinary)["period_axis"]
    assert ordinary["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert ordinary_axis["mode"] == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert [item["vietocr_transformer_surface"] for item in ordinary_axis["raw_date_evidence"]] == [
        "Số cuối kỳ",
        "Số đầu kỳ",
    ]
    assert {item["selection_mode"] for item in ordinary_axis["raw_date_evidence"]} == {
        "VIETOCR_RELATIVE_PERIOD_ROLE"
    }


def test_owner_inheritance_is_limited_to_the_immediate_preceding_page() -> None:
    target_records = _ordinary_records()[1:]
    immediate = maturity.build_loan_maturity_variant_graph_document_v2(
        [
            _page([_record("Trang thuyết minh", 40, 20)], page_sequence=1),
            _page([_record("Cho vay khách hàng", 40, 20)], page_sequence=2),
            _page(target_records, page_sequence=3),
        ]
    )
    assert immediate["status"] == "ACCEPTED_VARIANT_GRAPH"
    assert _graph(immediate)["owner"]["mode"] == "IMMEDIATE_PRECEDING_PAGE"

    intervening = maturity.build_loan_maturity_variant_graph_document_v2(
        [
            _page([_record("Cho vay khách hàng", 40, 20)], page_sequence=1),
            _page([_record("Phân tích chất lượng nợ cho vay", 40, 20)], page_sequence=2),
            _page(target_records, page_sequence=3),
        ]
    )
    assert intervening["status"] == "UNRESOLVED"
    assert "CUSTOMER_LOAN_OWNER_NOT_RESOLVED" in _graph(intervening)["unresolved_reasons"]


def test_numeric_conflict_fails_closed_when_primary_surface_breaks_total() -> None:
    records = _ordinary_records()
    medium_comparative = next(
        record for record in records if record["vietocr_text"] == "21" and record["bbox"][0] == 850
    )
    medium_comparative["source_text"] = "1"

    result = maturity.build_loan_maturity_variant_graph_document_v2([_page(records)])

    assert result["status"] == "UNRESOLVED"
    assert "THREE_BUCKET_CORE_TOTAL_NOT_CORROBORATED" in _graph(result)["unresolved_reasons"]
    selected = _graph(result)["rows"][1]["values"][1]
    assert selected["surface"] == "1"
    assert selected["semantic_surface"] == "21"


def test_duplicate_region_and_unowned_child_only_negative_fail_closed() -> None:
    first = _ordinary_records()
    second = _ordinary_records()
    for record in second:
        record["bbox"][1] += 450
        record["bbox"][3] += 450
    duplicate = maturity.build_loan_maturity_variant_graph_document_v2([_page([*first, *second])])
    assert duplicate["status"] == "UNRESOLVED"
    assert duplicate["uniqueness"]["complete_region_count"] == 2

    children_only = [
        _record("Nợ ngắn hạn", 100, 100),
        _record("Nợ trung hạn", 100, 150),
        _record("Nợ dài hạn", 100, 200),
    ]
    negative = maturity.build_loan_maturity_variant_graph_document_v2([_page(children_only)])
    assert negative["status"] == "UNRESOLVED"


def test_hash_and_cached_scan_identity_tampering_are_rejected() -> None:
    pages = [_page(_ordinary_records())]
    result = maturity.build_loan_maturity_variant_graph_document_v2(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["values"][0]["surface"] = "999"
    with pytest.raises(maturity.LoanMaturityVariantGraphV2Error):
        maturity.validate_loan_maturity_variant_graph_document_v2(forged)

    forged_scan = copy.deepcopy(result["region_scan"])
    forged_scan["regions"][0]["page_sequence"] = 99
    with pytest.raises(maturity.LoanMaturityVariantGraphV2Error):
        maturity.build_loan_maturity_variant_graph_from_topology_scan_v2(pages, forged_scan)
