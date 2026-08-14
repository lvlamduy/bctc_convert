from __future__ import annotations

import copy
import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_quality_variant_graph_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_quality_variant_graph_v1", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
quality = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = quality
_SPEC.loader.exec_module(quality)


def _page(
    surfaces: Sequence[tuple[str, int]],
    *,
    page_sequence: int = 1,
    primary_numeric_authority: bool = True,
) -> dict[str, object]:
    return {
        "lines": [
            {
                "bbox": [x, index * 20, x + 80, index * 20 + 14],
                "source_line_index": index,
                "source_text": text if primary_numeric_authority else None,
                "vietocr_text": text,
            }
            for index, (text, x) in enumerate(surfaces)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _ordinary(
    *,
    branch: str = "Phân tích chất lượng nợ cho vay",
    standard: str = "Nợ đủ tiêu chuẩn",
    relative_periods: bool = False,
    nested: bool = False,
    additive: bool = False,
    wrong_total: bool = False,
) -> list[tuple[str, int]]:
    periods = (
        [("Số cuối kỳ", 300), ("Số đầu kỳ", 600)]
        if relative_periods
        else [("30/06/2026", 300), ("31/12/2025", 600)]
    )
    rows: list[tuple[str, int]] = [
        ("5. Cho vay khách hàng", 0),
        (branch, 0),
        *periods,
        ("Triệu đồng", 300),
        ("Triệu đồng", 600),
        ("Dư nợ cho vay", 0),
        (standard, 0),
        ("100", 300),
        ("90", 600),
    ]
    if nested:
        rows.extend(
            [
                ("% Trong đó các khoản cho vay tại công ty chứng khoán", 30),
                ("8", 300),
                ("7", 600),
            ]
        )
    rows.extend(
        [
            ("Nợ cần chú ý", 0),
            ("10", 300),
            ("9", 600),
            ("Nợ dưới tiêu chuẩn", 0),
            ("5", 300),
            ("4", 600),
            ("Nợ nghi ngờ", 0),
            ("3", 300),
            ("2", 600),
            ("Nợ có khả năng mất vốn", 0),
            ("2", 300),
            ("1", 600),
        ]
    )
    if additive:
        rows.extend(
            [
                ("Cho vay giao dịch ký quỹ và ứng trước tiền bán", 0),
                ("5", 300),
                ("4", 600),
                ("125" if not wrong_total else "126", 300),
                ("110", 600),
            ]
        )
    else:
        rows.extend(
            [
                ("120" if not wrong_total else "121", 300),
                ("106", 600),
            ]
        )
    rows.append(("Phân tích dư nợ theo thời gian", 0))
    return rows


def _stacked() -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = [
        ("Rủi ro tín dụng (tiếp theo)", 0),
        ("Phân loại chất lượng tài sản có rủi ro tín dụng", 0),
        ("30/06/2026", 100),
        ("31/12/2025", 300),
        ("Đơn vị: Triệu đồng", 0),
        ("Cho vay", 300),
        ("Mua nợ", 500),
        ("Chứng khoán đầu tư", 700),
        ("Tiền gửi TCTD", 100),
        ("Tổng cộng", 900),
        ("khách hàng", 300),
    ]
    role_labels = [
        "Nợ đủ tiêu chuẩn",
        "Nợ cần chú ý",
        "Nợ dưới tiêu chuẩn",
        "Nợ nghi ngờ",
        "Nợ có khả năng mất vốn",
    ]
    block_one = [
        [10, 20, 30, 40, 100],
        [1, 2, 3, 4, 10],
        [2, 3, 4, 5, 14],
        [3, 4, 5, 6, 18],
        [4, 5, 6, 7, 22],
    ]
    block_two = [[value * 2 for value in row] for row in block_one]
    for block in (block_one, block_two):
        for label, values in zip(role_labels, block, strict=True):
            result.append((label, 0))
            result.extend(
                (str(value), x) for value, x in zip(values, [100, 300, 500, 700, 900], strict=True)
            )
        totals = [sum(row[index] for row in block) for index in range(5)]
        result.extend(
            (str(value), x) for value, x in zip(totals, [100, 300, 500, 700, 900], strict=True)
        )
    return result


def test_horizontal_relative_period_variant_closes_without_bank_routing() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1(
        [
            _page(
                _ordinary(
                    branch="Phân tích dư nợ cho vay theo chất lượng nợ",
                    relative_periods=True,
                )
            )
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    graph = result["graphs"][0]
    assert graph["layout_mode"] == "HORIZONTAL_TYPED_PERIOD_LANES"
    assert graph["period_mode"] == "LOCAL_RELATIVE_PERIOD_ROLES"
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"
    assert [row["role"] for row in graph["rows"]] == [
        "STANDARD",
        "SPECIAL_MENTION",
        "SUBSTANDARD",
        "DOUBTFUL",
        "LOSS",
    ]
    assert result["safety"]["mapping_authority"] is False


def test_wrapped_owner_branch_intermediate_and_grade_labels_share_one_graph() -> None:
    replacements = {
        "5. Cho vay khách hàng": ["5. Cho vay", "khách hàng"],
        "Phân tích chất lượng nợ cho vay": ["Phân tích chất lượng", "nợ cho vay"],
        "Dư nợ cho vay": ["Dư nợ", "cho vay"],
        "Nợ đủ tiêu chuẩn": ["Nợ đủ", "tiêu chuẩn"],
        "Nợ cần chú ý": ["Nợ cần", "chú ý"],
        "Nợ dưới tiêu chuẩn": ["Nợ dưới", "tiêu chuẩn"],
        "Nợ nghi ngờ": ["Nợ nghi", "ngờ"],
        "Nợ có khả năng mất vốn": ["Nợ có khả năng", "mất vốn"],
    }
    wrapped: list[tuple[str, int]] = []
    for surface, x in _ordinary():
        wrapped.extend((fragment, x) for fragment in replacements.get(surface, [surface]))

    result = quality.build_loan_quality_variant_graph_document_v1([_page(wrapped)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["owner_context"]["surface"] == "5. Cho vay khách hàng"
    assert graph["branch"]["surface"] == "Phân tích chất lượng nợ cho vay"
    assert [row["label"]["surface"] for row in graph["rows"]] == [
        "Nợ đủ tiêu chuẩn",
        "Nợ cần chú ý",
        "Nợ dưới tiêu chuẩn",
        "Nợ nghi ngờ",
        "Nợ có khả năng mất vốn",
    ]


def test_owner_and_document_unit_can_be_inherited_only_from_preceding_evidence() -> None:
    target = [
        item for item in _ordinary() if item[0] not in {"5. Cho vay khách hàng", "Triệu đồng"}
    ]
    result = quality.build_loan_quality_variant_graph_document_v1(
        [
            _page(
                [("Đơn vị: Triệu đồng", 0), ("5. Cho vay khách hàng", 0)],
                page_sequence=1,
            ),
            _page(target, page_sequence=2),
        ]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["owner_context"]["mode"] == "IMMEDIATE_PREVIOUS_PAGE"
    assert graph["unit_scope"]["mode"] == "INHERITED_DOCUMENT_MONEY_UNIT"


def test_accentless_error_and_nonadditive_within_standard_are_retained() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1(
        [_page(_ordinary(standard="Nơ dủ tiêu chuản", nested=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["rows"][0]["label"]["match_kind"] == "EXACT_ACCENTLESS_ALIAS"
    assert graph["nonadditive_rows"] == [
        {
            "classification": "NONADDITIVE_INCLUDED_DISCLOSURE",
            "label_source_line_indices": [10],
            "label_surface": "% Trong đó các khoản cho vay tại công ty chứng khoán",
            "parent_role": "STANDARD",
            "values": graph["nonadditive_rows"][0]["values"],
        }
    ]
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"


def test_additive_margin_is_not_folded_into_any_grade() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1([_page(_ordinary(additive=True))])

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert graph["optional_additive_row"]["classification"] == ("ADDITIVE_MARGIN_OR_ADVANCE_CHILD")
    assert graph["totals"]["core"] == []
    assert graph["totals"]["grand"]
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"


def test_optional_core_subtotal_can_precede_additive_row_and_grand_total() -> None:
    surfaces = _ordinary(additive=True)
    margin = next(
        index
        for index, item in enumerate(surfaces)
        if item[0] == "Cho vay giao dịch ký quỹ và ứng trước tiền bán"
    )
    surfaces[margin:margin] = [("120", 300), ("106", 600)]
    result = quality.build_loan_quality_variant_graph_document_v1([_page(surfaces)])

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert graph["totals"]["core"]
    assert graph["totals"]["grand"]
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"


def test_dotted_money_total_is_not_confused_with_the_following_note_number() -> None:
    surfaces = [
        ("5. Cho vay khách hàng", 0),
        ("Phân tích chất lượng nợ cho vay", 0),
        ("30/06/2026", 300),
        ("31/12/2025", 600),
        ("Triệu đồng", 300),
        ("Triệu đồng", 600),
        ("Nợ đủ tiêu chuẩn", 0),
        ("1.000", 300),
        ("900", 600),
        ("Nợ cần chú ý", 0),
        ("100", 300),
        ("90", 600),
        ("Nợ dưới tiêu chuẩn", 0),
        ("50", 300),
        ("40", 600),
        ("Nợ nghi ngờ", 0),
        ("30", 300),
        ("20", 600),
        ("Nợ có khả năng mất vốn", 0),
        ("20", 300),
        ("10", 600),
        ("1.200", 300),
        ("1.060", 600),
        ("10.2", 0),
        ("Phân tích dư nợ theo thời gian", 0),
    ]
    result = quality.build_loan_quality_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert result["graphs"][0]["arithmetic_status"] == ("CORROBORATED_GRADE_POPULATION")


def test_unlabeled_total_excludes_a_distant_numeric_page_footer() -> None:
    surfaces = _ordinary()[:-1]
    surfaces.append(("26", 700))
    page = _page(surfaces)
    page["lines"][-1]["bbox"][1] += 500
    page["lines"][-1]["bbox"][3] += 500

    result = quality.build_loan_quality_variant_graph_document_v1([page])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [item["surface"] for item in graph["totals"]["core"]] == ["120", "106"]


def test_four_lane_money_percentage_axis_is_preserved_and_closed() -> None:
    surfaces: list[tuple[str, int]] = [
        ("5. Cho vay khách hàng", 0),
        ("Phân tích chất lượng nợ cho vay", 0),
        ("30/06/2026", 200),
        ("31/12/2025", 600),
        ("Triệu đồng", 200),
        ("%", 400),
        ("Triệu đồng", 600),
        ("%", 800),
    ]
    rows = [
        ("Nợ đủ tiêu chuẩn", [100, 50, 90, 50]),
        ("Nợ cần chú ý", [40, 20, 36, 20]),
        ("Nợ dưới tiêu chuẩn", [30, 15, 27, 15]),
        ("Nợ nghi ngờ", [20, 10, 18, 10]),
        ("Nợ có khả năng mất vốn", [10, 5, 9, 5]),
    ]
    for label, values in rows:
        surfaces.append((label, 0))
        surfaces.extend(
            (str(value), x) for value, x in zip(values, [200, 400, 600, 800], strict=True)
        )
    surfaces.extend([("200", 200), ("100", 400), ("180", 600), ("100", 800)])
    result = quality.build_loan_quality_variant_graph_document_v1([_page(surfaces)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [item["lane_type"] for item in graph["rows"][0]["values"]] == [
        "MONEY",
        "PERCENT",
        "MONEY",
        "PERCENT",
    ]
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"


def test_stacked_period_multi_asset_variant_selects_column_by_geometry() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1([_page(_stacked())])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["layout_mode"] == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
    assert graph["customer_loan_column"]["column_index"] == 1
    assert graph["total_column"]["column_index"] == 4
    assert len(graph["blocks"]) == 2
    assert graph["arithmetic_status"] == ("CORROBORATED_STACKED_ROW_AND_COLUMN_POPULATIONS")


def test_inline_narrative_branch_and_sparse_companion_cells_share_the_stacked_graph() -> None:
    surfaces = _stacked()
    surfaces[1] = (
        "2.10% (31/12/2025: 2,16%). Chi tiết phân loại chất lượng tài sản có rủi ro "
        "tín dụng tại Ngân hàng như sau",
        0,
    )
    sparse: list[tuple[str, int]] = []
    current_role: str | None = None
    remaining_role_values = 0
    role_labels = {
        "Nợ đủ tiêu chuẩn",
        "Nợ cần chú ý",
        "Nợ dưới tiêu chuẩn",
        "Nợ nghi ngờ",
        "Nợ có khả năng mất vốn",
    }
    for surface, x in surfaces:
        if surface in role_labels:
            current_role = surface
            remaining_role_values = 5
            sparse.append((surface, x))
            continue
        if (
            current_role is not None
            and remaining_role_values > 0
            and surface.replace(".", "").isdigit()
        ):
            if current_role == "Nợ đủ tiêu chuẩn" or x in {300, 900}:
                sparse.append((surface, x))
            remaining_role_values -= 1
            if remaining_role_values == 0:
                current_role = None
            continue
        current_role = None
        sparse.append((surface, x))

    result = quality.build_loan_quality_variant_graph_document_v1(
        [_page(sparse, primary_numeric_authority=False)]
    )

    assert result["status"] == "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    graph = result["graphs"][0]
    assert graph["branch"]["variant"] == "CREDIT_RISK_ASSET_QUALITY_WORDING"
    assert graph["owner_context"]["surface"] == "Rủi ro tín dụng (tiếp theo)"
    assert graph["customer_loan_column"]["column_index"] == 1
    assert graph["total_column"]["column_index"] == 4
    assert [item["lane_index"] for item in graph["blocks"][0]["rows"][1]["values"]] == [
        1,
        4,
    ]
    assert result["safety"]["blank_companion_cells_imputed_as_zero"] is False


def test_stacked_period_role_labels_may_wrap_without_a_separate_parser() -> None:
    replacements = {
        "Nợ đủ tiêu chuẩn": ["Nợ đủ", "tiêu chuẩn"],
        "Nợ cần chú ý": ["Nợ cần", "chú ý"],
        "Nợ dưới tiêu chuẩn": ["Nợ dưới", "tiêu chuẩn"],
        "Nợ nghi ngờ": ["Nợ nghi", "ngờ"],
        "Nợ có khả năng mất vốn": ["Nợ có khả năng", "mất vốn"],
    }
    wrapped: list[tuple[str, int]] = []
    for surface, x in _stacked():
        wrapped.extend((fragment, x) for fragment in replacements.get(surface, [surface]))

    result = quality.build_loan_quality_variant_graph_document_v1([_page(wrapped)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["layout_mode"] == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
    assert all(
        row["label"]["surface"] in replacements
        for block in graph["blocks"]
        for row in block["rows"]
    )


def test_stacked_companion_column_mismatch_vetoes_target_selection() -> None:
    surfaces = _stacked()
    first_value = next(index for index, item in enumerate(surfaces) if item == ("10", 100))
    surfaces[first_value] = ("11", 100)
    result = quality.build_loan_quality_variant_graph_document_v1([_page(surfaces)])

    assert result["graphs"][0]["status"] == "UNRESOLVED"
    assert "ARITHMETIC_POPULATION_VETO" in result["graphs"][0]["unresolved_reasons"]


def test_numeric_authority_absent_keeps_unique_structure_but_not_acceptance() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1(
        [_page(_ordinary(), primary_numeric_authority=False)]
    )

    assert result["status"] == "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    assert result["uniqueness"] == {"full_match_count": 1, "status": "UNIQUE_FULL_MATCH"}
    assert result["graphs"][0]["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
    assert result["graphs"][0]["arithmetic_status"] == (
        "NOT_EVALUATED_NO_PRIMARY_NUMERIC_AUTHORITY"
    )


def test_accounting_mismatch_vetoes_an_otherwise_complete_topology() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1(
        [_page(_ordinary(wrong_total=True))]
    )

    assert result["status"] == "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    assert result["graphs"][0]["status"] == "UNRESOLVED"
    assert "ARITHMETIC_POPULATION_VETO" in result["graphs"][0]["unresolved_reasons"]


def test_nearby_maturity_family_is_preserved_only_as_a_negative_control() -> None:
    surface = _ordinary()
    surface[1] = ("Phân tích dư nợ theo thời gian", 0)
    result = quality.build_loan_quality_variant_graph_document_v1([_page(surface)])

    assert result["status"] == "UNRESOLVED_NO_COMPLETE_REGION"
    assert result["graphs"] == []
    assert result["metrics"]["near_region_count"] == 2
    assert {
        tuple(region["unresolved_reasons"]) for region in result["region_scan"]["near_regions"]
    } == {("BRANCH_VARIANT_NOT_RESOLVED",)}


def test_two_full_regions_are_not_silently_selected_by_page_or_bank() -> None:
    result = quality.build_loan_quality_variant_graph_document_v1(
        [_page(_ordinary(), page_sequence=1), _page(_ordinary(), page_sequence=2)]
    )

    assert result["status"] == "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    assert result["uniqueness"] == {"full_match_count": 2, "status": "MULTIPLE_FULL_MATCHES"}
    assert result["metrics"]["accepted_graph_count"] == 2


def test_exact_replay_rejects_coordinated_persisted_tampering() -> None:
    pages = [_page(_ordinary())]
    result = quality.build_loan_quality_variant_graph_document_v1(pages)
    assert quality.validate_loan_quality_variant_graph_replay_v1(result, pages) == result

    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["label"]["surface"] = "Nợ nhóm khác"
    material = copy.deepcopy(forged)
    material.pop("result_id")
    forged["result_id"] = "lqvgv1:document:" + quality.canonical_json_sha256_v1(material)
    with pytest.raises(quality.LoanQualityVariantGraphV1Error, match="replay exactly"):
        quality.validate_loan_quality_variant_graph_replay_v1(forged, pages)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda page: page.update(primary_numeric_authority=1),
        lambda page: page["lines"][0].update(source_line_index=True),
        lambda page: page["lines"][0].update(bbox=[0.0, 0, 1, 1]),
    ],
)
def test_input_contract_rejects_bool_float_type_smuggling(mutation: object) -> None:
    page = _page(_ordinary())
    mutation(page)
    with pytest.raises(quality.LoanQualityVariantGraphV1Error):
        quality.build_loan_quality_variant_graph_document_v1([page])
