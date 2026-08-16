from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_type_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_type_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
loan_type = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = loan_type
_SPEC.loader.exec_module(loan_type)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 120, y + 24],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _direct(*, reordered: bool = False, missing_dash: bool = False) -> list[tuple[str, int, int]]:
    rows = [
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", "100", "90"),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", "10", "9"),
        ("Cho thuê tài chính", "5", "4"),
        ("Các khoản trả thay khách hàng", "3", "2"),
        ("Cho vay bằng vốn tài trợ, ủy thác đầu tư", "2", "1"),
    ]
    if reordered:
        rows = [rows[0], rows[4], rows[1], rows[3], rows[2]]
    result: list[tuple[str, int, int]] = [
        ("5. CHO VAY KHÁCH HÀNG", 0, 0),
        ("30/06/2026", 500, 40),
        ("31/12/2025", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
    ]
    for row_index, (label, current, previous) in enumerate(rows):
        y = 120 + row_index * 45
        result.append((label, 0, y))
        if not (missing_dash and "ủy thác" in label):
            result.extend([(current, 500, y), (previous, 800, y)])
    current_total = sum(int(row[1]) for row in rows) - (2 if missing_dash else 0)
    previous_total = sum(int(row[2]) for row in rows) - (1 if missing_dash else 0)
    result.extend(
        [
            (str(current_total), 500, 120 + len(rows) * 45),
            (str(previous_total), 800, 120 + len(rows) * 45),
            ("Phân tích chất lượng nợ cho vay", 0, 400),
        ]
    )
    return result


def _subtotal_margin() -> list[tuple[str, int, int]]:
    result = _direct()[:-3]
    result.extend(
        [
            ("120", 500, 345),
            ("106", 800, 345),
            ("Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS", 0, 390),
            ("5", 500, 390),
            ("4", 800, 390),
            ("125", 500, 435),
            ("110", 800, 435),
            ("Phân tích chất lượng nợ cho vay", 0, 480),
        ]
    )
    return result


def _percent_lanes() -> list[tuple[str, int, int]]:
    rows = [
        ("Cho vay các tổ chức kinh tế và cá nhân trong nước", "90", "90", "80", "80"),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", "5", "5", "10", "10"),
        ("Các khoản trả thay khách hàng", "3", "3", "4", "4"),
        ("Cấp tín dụng khác", "2", "2", "6", "6"),
    ]
    result: list[tuple[str, int, int]] = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Ngày 31 tháng 3 năm 2026", 400, 35),
        ("Ngày 31 tháng 12 năm 2025", 900, 35),
        ("Triệu đồng", 400, 70),
        ("%", 600, 70),
        ("Triệu đồng", 900, 70),
        ("%", 1100, 70),
    ]
    for offset, row in enumerate(rows):
        y = 120 + offset * 50
        result.append((row[0], 0, y))
        result.extend(
            [
                (row[1], 400, y),
                (row[2], 600, y),
                (row[3], 900, y),
                (row[4], 1100, y),
            ]
        )
    result.extend(
        [
            ("100", 400, 330),
            ("100", 600, 330),
            ("100", 900, 330),
            ("100", 1100, 330),
            ("10.1", 0, 375),
            ("Phân tích chất lượng nợ cho vay", 0, 410),
        ]
    )
    return result


def test_direct_total_accepts_reordered_children_without_bank_routing() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_direct(reordered=True))])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "ENTRUSTED_OR_SPONSORED_CAPITAL",
        "DISCOUNT_INSTRUMENTS",
        "PAYMENTS_ON_BEHALF",
        "FINANCIAL_LEASE",
    ]
    assert graph["layout_mode"] == "TWO_MONEY_LANES"
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )
    assert result["safety"]["bank_filename_note_or_page_used_for_inference"] is False


def test_owner_plus_two_children_can_be_unique_when_axes_total_and_closure_agree() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("31/12/2025", 500, 40),
        ("31/12/2024", 800, 40),
        ("Triệu đồng", 500, 70),
        ("Triệu đồng", 800, 70),
        ("Cho vay các tổ chức kinh tế, cá nhân trong nước", 0, 120),
        ("100", 500, 120),
        ("90", 800, 120),
        ("Cho vay chiết khấu công cụ chuyển nhượng và các giấy tờ có giá", 0, 165),
        ("10", 500, 165),
        ("9", 800, 165),
        ("110", 500, 210),
        ("99", 800, 210),
        ("Phân tích chất lượng nợ cho vay", 0, 255),
    ]
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == [
        "DOMESTIC_ORGANIZATIONS_INDIVIDUALS",
        "DISCOUNT_INSTRUMENTS",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_missing_dash_cells_are_not_imputed_as_zero() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(_direct(missing_dash=True))]
    )

    graph = result["graphs"][0]
    entrusted = next(
        row for row in graph["rows"] if row["role"] == "ENTRUSTED_OR_SPONSORED_CAPITAL"
    )
    assert [value["status"] for value in entrusted["values"]] == [
        "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
        "SEMANTIC_CELL_ABSENT_NOT_IMPUTED",
    ]
    assert all(
        check["status"] == "UNRESOLVED_MISSING_SEMANTIC_CELL_NOT_IMPUTED"
        for check in graph["accounting_checks"]
    )


def test_core_subtotal_then_margin_then_grand_total_is_one_generic_variant() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_subtotal_margin())])

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert len(graph["intermediate_totals"]) == 1
    assert [item["semantic_surface"] for item in graph["intermediate_totals"][0]] == [
        "120",
        "106",
    ]
    assert [item["semantic_surface"] for item in graph["total"]] == ["125", "110"]
    assert graph["rows"][-1]["role"] == "MARGIN_AND_SECURITIES_ADVANCE"


def test_money_percent_companion_lanes_and_broad_other_credit_are_preserved() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1([_page(_percent_lanes())])

    graph = result["graphs"][0]
    assert graph["lane_types"] == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert graph["layout_mode"] == "MONEY_PERCENT_COMPANION_LANES"
    assert graph["rows"][-1]["role"] == "UNMAPPED_OTHER_CREDIT"
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_wrapped_label_may_be_interleaved_with_numeric_geometry() -> None:
    surfaces = _direct()
    discount = next(
        index for index, item in enumerate(surfaces) if item[0].startswith("Cho vay chiết khấu")
    )
    _label, _x, y = surfaces[discount]
    surfaces[discount : discount + 3] = [
        ("Cho vay chiết khấu công cụ chuyển nhượng và", 0, y),
        ("10", 500, y),
        ("9", 800, y),
        ("các giấy tờ có giá", 0, y + 18),
    ]

    result = loan_type.build_loan_type_variant_graph_document_v1([_page(surfaces)])

    graph = result["graphs"][0]
    discount_row = next(row for row in graph["rows"] if row["role"] == "DISCOUNT_INSTRUMENTS")
    assert discount_row["label"]["source_line_indices"] == [8, 11]
    assert [item["semantic_surface"] for item in discount_row["values"]] == ["10", "9"]


def test_wrong_family_and_insufficient_child_subset_remain_near_unresolved() -> None:
    page = _page(
        [
            ("Cho vay khách hàng", 0, 0),
            ("30/06/2026", 500, 40),
            ("31/12/2025", 800, 40),
            ("Triệu đồng", 500, 70),
            ("Triệu đồng", 800, 70),
            ("Nợ ngắn hạn", 0, 120),
            ("100", 500, 120),
            ("90", 800, 120),
            ("Nợ trung hạn", 0, 165),
            ("50", 500, 165),
            ("40", 800, 165),
            ("150", 500, 210),
            ("130", 800, 210),
        ]
    )
    result = loan_type.build_loan_type_variant_graph_document_v1([page])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["graphs"] == []
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "INSUFFICIENT_DISTINCT_LOAN_TYPE_ROLES"
    ]


def test_two_full_tables_in_one_document_fail_uniqueness() -> None:
    result = loan_type.build_loan_type_variant_graph_document_v1(
        [_page(_direct(), page_sequence=1), _page(_direct(), page_sequence=2)]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"] == {
        "full_match_count": 2,
        "status": "AMBIGUOUS_MULTIPLE_FULL_MATCHES",
    }


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_direct())]
    result = loan_type.build_loan_type_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "ltvgv1:result:" + loan_type.canonical_json_sha256_v1(material)

    with pytest.raises(loan_type.LoanTypeVariantGraphV1Error, match="replay exactly"):
        loan_type.validate_loan_type_variant_graph_replay_v1(forged, pages)
