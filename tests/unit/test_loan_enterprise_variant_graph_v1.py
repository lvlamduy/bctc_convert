from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_enterprise_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_enterprise_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
loan_enterprise = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = loan_enterprise
_SPEC.loader.exec_module(loan_enterprise)


def _page(
    surfaces: list[tuple[str, int, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = False,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, y, x + 140, y + 24],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x, y) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _headers(
    *, owner: str = "CHO VAY KHÁCH HÀNG", four_lanes: bool = True
) -> list[tuple[str, int, int]]:
    values: list[tuple[str, int, int]] = [
        (owner, 0, 0),
        (
            "Phân tích dư nợ cho vay theo đối tượng khách hàng và theo loại hình doanh nghiệp",
            0,
            35,
        ),
        ("30/06/2026", 500, 75),
        ("31/12/2025", 900, 75),
        ("Triệu đồng", 500, 105),
    ]
    if four_lanes:
        values.extend(
            [
                ("%", 700, 105),
                ("Triệu đồng", 900, 105),
                ("%", 1100, 105),
            ]
        )
    else:
        values.append(("Triệu đồng", 900, 105))
    return values


def _flat_enterprise(*, reordered: bool = False) -> list[tuple[str, int, int]]:
    rows = [
        ("Công ty Nhà nước", 10, "10", 9, "9"),
        ("Công ty TNHH MTV Vốn Nhà nước 100%", 20, "20", 18, "18"),
        ("Công ty TNHH khác", 10, "10", 12, "12"),
        ("Công ty cổ phần khác", 20, "20", 21, "21"),
        ("Doanh nghiệp tư nhân", 15, "15", 14, "14"),
        ("Hộ kinh doanh, cá nhân", 25, "25", 26, "26"),
    ]
    if reordered:
        rows = [rows[5], rows[2], rows[0], rows[4], rows[1], rows[3]]
    result = _headers()
    for offset, (label, current, current_percent, previous, previous_percent) in enumerate(rows):
        y = 150 + offset * 48
        result.extend(
            [
                (label, 0, y),
                (str(current), 500, y),
                (current_percent, 700, y),
                (str(previous), 900, y),
                (previous_percent, 1100, y),
            ]
        )
    total_y = 150 + len(rows) * 48
    result.extend(
        [
            ("100", 500, total_y),
            ("100", 700, total_y),
            ("100", 900, total_y),
            ("100", 1100, total_y),
            ("Phân tích dư nợ cho vay theo ngành", 0, total_y + 45),
        ]
    )
    return result


def _two_lane_with_missing_cell() -> list[tuple[str, int, int]]:
    rows: list[tuple[str, str | None, str]] = [
        ("Công ty Nhà nước", "10", "9"),
        ("Công ty TNHH khác", "20", "18"),
        ("Công ty cổ phần khác", "30", "27"),
        ("Doanh nghiệp tư nhân", None, "1"),
        ("Hộ kinh doanh, cá nhân", "20", "22"),
        ("Thành phần kinh tế khác", "20", "23"),
    ]
    result = _headers(four_lanes=False)
    for offset, (label, current, previous) in enumerate(rows):
        y = 150 + offset * 45
        result.append((label, 0, y))
        if current is not None:
            result.append((current, 500, y))
        result.append((previous, 900, y))
    result.extend([("100", 500, 430), ("100", 900, 430)])
    return result


def _grouped_enterprise() -> list[tuple[str, int, int]]:
    result = _headers()
    rows = [
        # Unmapped source group parent.  Its numeric row becomes an intermediate total.
        ("Cho vay các TCKT", 60, "60", 57, "57", False),
        ("Công ty Nhà nước", 10, "10", 9, "9", True),
        ("Công ty TNHH khác", 20, "20", 18, "18", True),
        ("Công ty cổ phần khác", 30, "30", 30, "30", True),
        ("Cho vay cá nhân", 20, "20", 22, "22", False),
        ("Hộ kinh doanh, cá nhân", 20, "20", 22, "22", True),
        ("Cho vay khác", 10, "10", 11, "11", False),
        ("Đơn vị hành chính sự nghiệp, Đoàn thể và hiệp hội", 4, "4", 5, "5", True),
        ("Khác", 6, "6", 6, "6", True),
        (
            "Cho vay tại Chi nhánh và ngân hàng con nước ngoài",
            10,
            "10",
            10,
            "10",
            True,
        ),
        # Core subtotal is source-only intermediate evidence.
        ("Dư nợ cho vay", 100, "100", 100, "100", False),
        (
            "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
            5,
            "5",
            4,
            "4",
            True,
        ),
    ]
    for offset, (label, current, current_percent, previous, previous_percent, _mapped) in enumerate(
        rows
    ):
        y = 150 + offset * 45
        result.extend(
            [
                (label, 0, y),
                (str(current), 500, y),
                (current_percent, 700, y),
                (str(previous), 900, y),
                (previous_percent, 1100, y),
            ]
        )
    total_y = 150 + len(rows) * 45
    result.extend(
        [
            ("105", 500, total_y),
            ("105", 700, total_y),
            ("104", 900, total_y),
            ("104", 1100, total_y),
        ]
    )
    return result


def test_flat_reordered_four_lane_table_forms_one_generic_graph() -> None:
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [_page(_flat_enterprise(reordered=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["branch"]["schema_concept"] == "PHAN_TICH_THEO_LOAI_HINH_DOANH_NGHIEP"
    assert graph["lane_types"] == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert graph["anchor_resolution"]["selected_size"] == 2
    assert graph["anchor_resolution"]["selected_anchor_keys"][0] == (
        "PARENT:LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION"
    )
    assert [row["role"] for row in graph["rows"]] == [
        "HOUSEHOLD_INDIVIDUAL",
        "OTHER_LLC",
        "STATE_ENTERPRISE",
        "PRIVATE_ENTERPRISE",
        "STATE_OWNED_SINGLE_MEMBER_LLC",
        "OTHER_JOINT_STOCK",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_parent_plus_one_child_can_uniquely_locate_the_full_region() -> None:
    surfaces = _headers()
    surfaces.extend(
        [
            ("Hộ kinh doanh, cá nhân", 0, 150),
            ("100", 500, 150),
            ("100", 700, 150),
            ("100", 900, 150),
            ("100", 1100, 150),
            ("100", 500, 198),
            ("100", 700, 198),
            ("100", 900, 198),
            ("100", 1100, 198),
        ]
    )

    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == ["HOUSEHOLD_INDIVIDUAL"]
    assert graph["anchor_resolution"] == {
        "anchor_search_scope": "ALL_COMPLETE_AND_NEAR_BRANCH_REGIONS_IN_FULL_DOCUMENT",
        "child_priority_basis": "SEMANTIC_MONEY_MAGNITUDE_DISCOVERY_ONLY",
        "matching_region_count": 1,
        "pair_combinations_exhausted_before_triples": True,
        "selected_anchor_keys": [
            "PARENT:LOAN_ENTERPRISE_OR_CUSTOMER_TYPE_CLASSIFICATION",
            "CHILD:HOUSEHOLD_INDIVIDUAL",
        ],
        "selected_size": 2,
        "status": "UNIQUE_MINIMAL_ANCHOR_COMBINATION",
    }


def test_grouped_parents_subtotal_margin_and_grand_total_share_one_graph() -> None:
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [_page(_grouped_enterprise())]
    )

    graph = result["graphs"][0]
    assert "FOREIGN_BRANCH_LOANS_SOURCE_ONLY" in [row["role"] for row in graph["rows"]]
    assert "MARGIN_AND_SECURITIES_ADVANCE" in [row["role"] for row in graph["rows"]]
    # The leading population parent is header context; the later personal,
    # other-population, and core-subtotal rows remain explicit intermediates.
    assert len(graph["intermediate_totals"]) == 3
    assert [item["semantic_surface"] for item in graph["total"]] == [
        "105",
        "105",
        "104",
        "104",
    ]
    assert all(
        check["status"] == "CORROBORATED_SEMANTIC_PROPOSAL_ONLY"
        for check in graph["accounting_checks"]
    )


def test_exact_row_label_cannot_absorb_the_next_wrapped_role_across_value_lanes() -> None:
    surfaces = _headers()
    surfaces.extend(
        [
            ("Công ty TNHH khác", 0, 150),
            ("40", 500, 150),
            ("40", 700, 150),
            ("35", 900, 150),
            ("35", 1100, 150),
            ("Công ty Cổ phận Vốn Nhà nước - 50%", 0, 198),
            ("(Nhà nước chiếm cổ phần chi phối)", 0, 222),
            ("60", 500, 198),
            ("60", 700, 198),
            ("65", 900, 198),
            ("65", 1100, 198),
            ("100", 500, 270),
            ("100", 700, 270),
            ("100", 900, 270),
            ("100", 1100, 270),
        ]
    )

    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    rows = result["graphs"][0]["rows"]
    assert [row["role"] for row in rows] == [
        "OTHER_LLC",
        "STATE_CONTROLLED_JOINT_STOCK",
    ]
    assert rows[0]["label"]["source_line_indices"] == [8]
    assert rows[1]["label"]["source_line_indices"] == [13, 14]


def test_two_money_lanes_and_missing_cell_stay_structured_but_numeric_unresolved() -> None:
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [_page(_two_lane_with_missing_cell())]
    )

    graph = result["graphs"][0]
    assert graph["lane_types"] == ["MONEY", "MONEY"]
    assert graph["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
    assert graph["accounting_checks"][0]["status"] == (
        "UNRESOLVED_MISSING_SEMANTIC_CELL_NOT_IMPUTED"
    )
    assert graph["rows"][3]["values"][0]["status"] == "SEMANTIC_CELL_ABSENT_NOT_IMPUTED"


def test_deposit_table_with_same_branch_words_is_a_negative_control() -> None:
    surfaces = _flat_enterprise()
    surfaces[0] = ("TIỀN GỬI CỦA KHÁCH HÀNG", 0, 0)
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["graphs"] == []
    assert result["near_regions"][0]["unresolved_reasons"] == [
        "CUSTOMER_LOAN_OWNER_CONTEXT_NOT_RESOLVED"
    ]


def test_extended_period_mode_stops_at_a_second_credit_population() -> None:
    surfaces = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo đối tượng khách hàng", 0, 35),
        ("Số cuối năm", 500, 75),
        ("Số đầu năm", 900, 75),
        ("Triệu VND", 500, 105),
        ("Triệu VND", 900, 105),
        ("Công ty trách nhiệm hữu hạn", 0, 150),
        ("60", 500, 150),
        ("55", 900, 150),
        ("Công ty cổ phần", 0, 195),
        ("40", 500, 195),
        ("45", 900, 195),
        ("100", 500, 240),
        ("100", 900, 240),
        ("Nghiệp vụ phát hành thư tín dụng trả chậm", 0, 285),
        # These repeated legal forms belong to the separate population and
        # must not make the customer-loan family look internally duplicated.
        ("Công ty cổ phần", 0, 330),
        ("7", 500, 330),
        ("8", 900, 330),
    ]

    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [_page(surfaces)],
        enable_extended_reporting_period_variants=True,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [item["period"] for item in graph["period_axis"]] == [
        "CURRENT_PERIOD_END",
        "COMPARATIVE_PERIOD_START",
    ]
    assert [row["role"] for row in graph["rows"]] == [
        "OTHER_LLC",
        "OTHER_JOINT_STOCK",
    ]


def test_extended_mode_does_not_admit_an_industry_branch_with_one_shared_row() -> None:
    industry = [
        ("CHO VAY KHÁCH HÀNG", 0, 0),
        ("Phân tích dư nợ cho vay theo một số ngành kinh tế của khách hàng", 0, 35),
        ("31/12/2025", 500, 75),
        ("31/12/2024", 900, 75),
        ("Triệu đồng", 500, 105),
        ("Triệu đồng", 900, 105),
        ("Cho vay giao dịch ký quỹ và ứng trước tiền bán chứng khoán", 0, 150),
        ("100", 500, 150),
        ("90", 900, 150),
        ("100", 500, 195),
        ("90", 900, 195),
    ]

    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [_page(_flat_enterprise()), _page(industry, page_sequence=2)],
        enable_extended_reporting_period_variants=True,
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["graphs"][0]["page_sequence"] == 1


def test_two_complete_regions_fail_document_uniqueness() -> None:
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(
        [
            _page(_flat_enterprise(), page_sequence=1),
            _page(_flat_enterprise(reordered=True), page_sequence=2),
        ]
    )

    assert result["status"] == "UNRESOLVED_MULTIPLE_COMPLETE_REGIONS"
    assert result["uniqueness"] == {
        "full_match_count": 2,
        "status": "AMBIGUOUS_MULTIPLE_FULL_MATCHES",
    }


def test_bank_page_or_filename_routing_is_not_part_of_the_contract() -> None:
    page = _page(_flat_enterprise())
    page["bank_code"] = "FORBIDDEN"
    with pytest.raises(loan_enterprise.LoanEnterpriseVariantGraphV1Error, match="fields drifted"):
        loan_enterprise.build_loan_enterprise_variant_graph_document_v1([page])

    source = _MODULE_PATH.read_text(encoding="utf-8")
    for forbidden in ('"ACB"', '"MBB"', '"VPB"', '"HDB"', '"VCB"', '"CTG"', '"BID"', '"VIB"'):
        assert forbidden not in source


def test_public_replay_rejects_coordinated_graph_rehash() -> None:
    pages = [_page(_flat_enterprise())]
    result = loan_enterprise.build_loan_enterprise_variant_graph_document_v1(pages)
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["label"]["surface"] = "forged"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "levgv1:result:" + loan_enterprise.canonical_json_sha256_v1(material)

    with pytest.raises(loan_enterprise.LoanEnterpriseVariantGraphV1Error, match="replay exactly"):
        loan_enterprise.validate_loan_enterprise_variant_graph_replay_v1(forged, pages)
