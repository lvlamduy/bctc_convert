from __future__ import annotations

import copy
import importlib.util
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = _ROOT / "scripts/experiments/loan_quality_variant_graph_v2.py"
_SPEC = importlib.util.spec_from_file_location("loan_quality_variant_graph_v2", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
quality = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = quality
_SPEC.loader.exec_module(quality)

_ROLES = {
    "STANDARD": "Nợ đủ tiêu chuẩn",
    "SPECIAL_MENTION": "Nợ cần chú ý",
    "SUBSTANDARD": "Nợ dưới tiêu chuẩn",
    "DOUBTFUL": "Nợ nghi ngờ",
    "LOSS": "Nợ có khả năng mất vốn",
}
_CANONICAL_ROLES = list(_ROLES)
_SAME = object()


def _record(
    text: str,
    x: int,
    y: int,
    *,
    height: int = 32,
    source: str | None | object = _SAME,
    width: int = 180,
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
    primary_numeric_authority: bool = True,
) -> dict[str, Any]:
    return {
        "lines": [
            {**copy.deepcopy(record), "source_line_index": index}
            for index, record in enumerate(records)
        ],
        "page_sequence": page_sequence,
        "primary_numeric_authority": primary_numeric_authority,
    }


def _ordinary_records(
    *,
    provider_roles: Sequence[str] = tuple(_CANONICAL_ROLES),
    four_lanes: bool = False,
) -> list[dict[str, Any]]:
    y_by_role = {
        "STANDARD": 170,
        "SPECIAL_MENTION": 215,
        "SUBSTANDARD": 260,
        "DOUBTFUL": 305,
        "LOSS": 350,
    }
    money = {
        "STANDARD": (100, 90),
        "SPECIAL_MENTION": (10, 9),
        "SUBSTANDARD": (5, 4),
        "DOUBTFUL": (3, 2),
        "LOSS": (2, 1),
    }
    percentages = {
        "STANDARD": ("83.00%", "84.00%"),
        "SPECIAL_MENTION": ("8.00%", "8.00%"),
        "SUBSTANDARD": ("4.00%", "4.00%"),
        "DOUBTFUL": ("3.00%", "2.00%"),
        "LOSS": ("2.00%", "2.00%"),
    }
    result = [
        _record("5. Cho vay khách hàng", 40, 20, width=300),
        _record("Phân tích chất lượng nợ cho vay", 70, 55, width=420),
        _record("30/06/2026", 540, 90, width=110),
        _record("31/12/2025", 840, 90, width=110),
    ]
    if four_lanes:
        result.extend(
            [
                _record("Triệu đồng", 500, 125, width=120),
                _record("%", 650, 125, width=45),
                _record("Triệu đồng", 800, 125, width=120),
                _record("%", 950, 125, width=45),
            ]
        )
    else:
        result.extend(
            [
                _record("Triệu đồng", 550, 125, width=120),
                _record("Triệu đồng", 850, 125, width=120),
            ]
        )
    for role in provider_roles:
        y = y_by_role[role]
        result.append(_record(_ROLES[role], 100, y, width=310))
        if four_lanes:
            current, comparative = money[role]
            current_percent, comparative_percent = percentages[role]
            for surface, x in zip(
                (str(current), current_percent, str(comparative), comparative_percent),
                (500, 650, 800, 950),
                strict=True,
            ):
                result.append(_record(surface, x, y - 3, height=30, width=100))
        else:
            for surface, x in zip(money[role], (550, 850), strict=True):
                result.append(_record(str(surface), x, y - 3, height=30, width=120))
    if four_lanes:
        totals = ("120", "100.00%", "106", "100.00%")
        for surface, x in zip(totals, (500, 650, 800, 950), strict=True):
            result.append(_record(surface, x, 400, height=30, width=100))
    else:
        for surface, x in (("120", 550), ("106", 850)):
            result.append(_record(surface, x, 400, height=30, width=120))
    result.append(_record("Phân tích dư nợ theo thời gian", 70, 455, width=420))
    return result


def _stacked_records(*, merged_second_total: bool = False) -> list[dict[str, Any]]:
    result = [
        _record("Rủi ro tín dụng", 40, 20, width=260),
        _record(
            "Phân loại chất lượng tài sản có rủi ro tín dụng",
            50,
            55,
            width=620,
        ),
        _record("30/06/2026", 500, 90, width=110),
        _record("Đơn vị: Triệu đồng", 50, 120, width=240),
        _record("Cho vay", 500, 125, width=100),
        _record("khách hàng", 500, 155, width=100),
        _record("Mua nợ", 700, 140, width=100),
        _record("Chứng khoán đầu tư", 900, 140, width=130),
        _record("Tiền gửi TCTD khác", 1100, 140, width=140),
        _record("Tổng cộng", 1300, 140, width=100),
    ]
    block_one = [
        {0: 100, 1: 2, 2: 3, 3: 4, 4: 109},
        {0: 10, 4: 10},
        {0: 5, 1: 1, 4: 6},
        {0: 3, 2: 2, 4: 5},
        {0: 2, 4: 2},
    ]
    block_two = [{column: value * 2 for column, value in row.items()} for row in block_one]
    columns = [500, 700, 900, 1100, 1300]
    for role, values, y in zip(_CANONICAL_ROLES, block_one, range(220, 420, 40), strict=True):
        result.append(_record(_ROLES[role], 100, y, width=310))
        result.extend(
            _record(str(value), columns[column], y - 3, height=30, width=100)
            for column, value in sorted(values.items())
        )
    for surface, x in zip((120, 3, 5, 4, 132), columns, strict=True):
        result.append(_record(str(surface), x, 430, height=30, width=100))
    result.extend(
        _record(f"Dòng thuyết minh lặp {index}", 80, 470 + index * 2, height=12, width=360)
        for index in range(35)
    )
    result.append(_record("31/12/2025", 500, 570, width=110))
    for role, values, y in zip(_CANONICAL_ROLES, block_two, range(630, 830, 40), strict=True):
        result.append(_record(_ROLES[role], 100, y, width=310))
        result.extend(
            _record(str(value), columns[column], y - 3, height=30, width=100)
            for column, value in sorted(values.items())
        )
    second_totals = (240, 6, 10, 8, 264)
    if merged_second_total:
        for surface, x in zip(second_totals[:3], columns[:3], strict=True):
            result.append(_record(str(surface), x, 840, height=30, width=100))
        result.append(_record("8 264", 1100, 840, height=30, width=300))
    else:
        for surface, x in zip(second_totals, columns, strict=True):
            result.append(_record(str(surface), x, 840, height=30, width=100))
    result.append(_record("Phân tích dư nợ theo thời gian", 50, 900, width=430))
    return result


@pytest.mark.parametrize(
    "provider_roles",
    [
        ("STANDARD", "SUBSTANDARD", "SPECIAL_MENTION", "DOUBTFUL", "LOSS"),
        ("STANDARD", "SPECIAL_MENTION", "DOUBTFUL", "SUBSTANDARD", "LOSS"),
    ],
)
def test_visual_geometry_reorders_doc26_and_doc107_provider_permutations(
    provider_roles: Sequence[str],
) -> None:
    result = quality.build_loan_quality_variant_graph_document_v2(
        [_page(_ordinary_records(provider_roles=provider_roles))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [row["role"] for row in graph["rows"]] == _CANONICAL_ROLES
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"
    assert all(
        value["role"] == row["role"]
        and value["page_sequence"] == 1
        and value["block_ordinal"] is None
        for row in graph["rows"]
        for value in row["values"]
    )


def test_four_typed_lanes_retain_money_and_percent_population() -> None:
    result = quality.build_loan_quality_variant_graph_document_v2(
        [_page(_ordinary_records(four_lanes=True))]
    )

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert graph["lane_types"] == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert graph["arithmetic_status"] == "CORROBORATED_GRADE_POPULATION"
    assert [value["lane_index"] for value in graph["rows"][0]["values"]] == [0, 1, 2, 3]


def test_one_line_is_one_candidate_when_source_or_vietocr_is_numeric() -> None:
    records = _ordinary_records()
    numeric = [record for record in records if record["vietocr_text"] == "100"][0]
    numeric["vietocr_text"] = "I00"
    viet_only = [record for record in records if record["vietocr_text"] == "90"][0]
    viet_only["source_text"] = "not numeric"

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    graph = result["graphs"][0]
    assert graph["status"] == "ACCEPTED_STRUCTURE_NUMERIC_UNRESOLVED"
    standard = graph["rows"][0]["values"]
    assert len(standard) == 2
    assert len({value["source_line_index"] for value in standard}) == 2
    assert standard[0]["source_surface"] == "100"
    assert standard[0]["vietocr_surface"] == "I00"
    assert standard[0]["surface"] == "100"
    assert standard[1]["source_authoritative"] is False
    assert standard[1]["semantic_surface"] == "90"


def test_public_validation_and_exact_replay_reject_tampering() -> None:
    pages = [_page(_ordinary_records())]
    result = quality.build_loan_quality_variant_graph_document_v2(pages)

    assert quality.validate_loan_quality_variant_graph_document_v2(result) == result
    assert quality.validate_loan_quality_variant_graph_replay_v2(result, pages) == result
    forged = copy.deepcopy(result)
    forged["graphs"][0]["rows"][0]["values"][0]["surface"] = "101"
    with pytest.raises(quality.LoanQualityVariantGraphV2Error):
        quality.validate_loan_quality_variant_graph_document_v2(forged)


def test_adjacent_branch_seeds_deduplicate_only_identical_bound_graph() -> None:
    records = _ordinary_records()
    records.insert(
        2,
        _record("Theo chất lượng nợ cho vay", 90, 70, height=28, width=350),
    )

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert len(result["graphs"]) == 1
    assert result["graphs"][0]["branch_alternative_count"] == 2


def test_excluded_footnote_binds_two_tokens_and_independent_prior_owner_total() -> None:
    prior = _page(
        [
            _record("4. Cho vay khách hàng", 40, 40, width=320),
            _record("125", 550, 300, width=120),
            _record("110", 850, 300, width=120),
        ],
        page_sequence=1,
    )
    records = _ordinary_records()[1:-1]
    records.extend(
        [
            _record(
                "(?) Không bao gồm 5 triệu đồng (31.12.2025: 4 triệu đồng) cho vay giao",
                70,
                438,
                height=50,
                width=880,
            ),
            _record(
                "dịch ký quỹ của Công ty chứng khoán.",
                100,
                480,
                height=38,
                width=520,
            ),
            _record("Phân tích dư nợ theo thời gian", 70, 550, width=420),
        ]
    )
    current = _page(records, page_sequence=2)

    result = quality.build_loan_quality_variant_graph_document_v2([prior, current])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    excluded = [
        row
        for row in graph["nonadditive_rows"]
        if row["classification"] == "NONADDITIVE_EXCLUDED_DISCLOSURE"
    ][0]
    assert excluded["label_source_line_indices"][-2:] == [22, 23]
    assert [value["surface"] for value in excluded["values"]] == ["5", "4"]
    assert [value["embedded_token_ordinal"] for value in excluded["values"]] == [0, 1]
    assert all(value["source_line_index"] == 22 for value in excluded["values"])
    assert [value["surface"] for value in graph["totals"]["core"]] == ["120", "106"]
    assert [value["surface"] for value in graph["totals"]["customer_loan_parent"]] == ["125", "110"]
    assert graph["owner_context"]["mode"] == "IMMEDIATE_PREVIOUS_PAGE"


def test_deferred_lc_boundary_excludes_post_boundary_grade_and_total() -> None:
    records = _ordinary_records()
    reset = records.pop()
    total = records[-2:]
    del records[-2:]
    records[6:6] = [
        _record("120", 550, 140, height=30, width=120),
        _record("106", 850, 140, height=30, width=120),
    ]
    records.extend(
        [
            _record("Nghiệp vụ phát hành thư tín dụng trả chậm", 70, 382, width=520),
            _record("Nợ đủ tiêu chuẩn", 100, 420, width=310),
            _record("999", 550, 420, height=30, width=120),
            _record("999", 850, 420, height=30, width=120),
            *total,
            {**reset, "bbox": [70, 520, 490, 552]},
        ]
    )

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    graph = result["graphs"][0]
    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert graph["table_bottom_y"] == 382
    assert all(row["label"]["source_line_indices"][0] < 23 for row in graph["rows"])
    assert [value["surface"] for value in graph["totals"]["core"]] == ["120", "106"]
    retained = {value["surface"] for row in graph["rows"] for value in row["values"]}
    assert "999" not in retained


def test_repeated_header_stacked_blocks_keep_sparse_blanks_not_zero() -> None:
    result = quality.build_loan_quality_variant_graph_document_v2(
        [_page(_stacked_records(merged_second_total=True))]
    )

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert graph["layout_mode"] == "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
    assert graph["period_mode"] == "LOCAL_PERIOD_OBSERVATION_PER_STACKED_BLOCK"
    assert len(graph["blocks"]) == 2
    assert [block["period"]["period"] for block in graph["blocks"]] == [
        "30/06/2026",
        "31/12/2025",
    ]
    assert graph["arithmetic_status"] == "CORROBORATED_STACKED_REQUIRED_TARGET_POPULATIONS"
    assert [check["status"] for check in graph["accounting_checks"]["target_column_checks"]] == [
        "CORROBORATED",
        "CORROBORATED",
    ]
    assert "NOT_EVALUATED_INCOMPLETE_VISIBLE_COLUMN" in {
        check["status"] for check in graph["accounting_checks"]["companion_column_checks"]
    }
    assert result["safety"]["blank_companion_cells_imputed_as_zero"] is False
    merged = graph["blocks"][1]["total"][-2:]
    assert [value["surface"] for value in merged] == ["8", "264"]
    assert merged[0]["source_line_index"] == merged[1]["source_line_index"]
    assert [value["source_surface"] for value in merged] == ["8", "264"]
    assert all(value["source_line_surface"] == "8 264" for value in merged)


def test_center_axis_retains_wide_first_lane_stacked_totals() -> None:
    records = _stacked_records()
    for record in records:
        if record["vietocr_text"] in {"120", "240"}:
            top = record["bbox"][1]
            record["bbox"] = [390, top, 610, top + 30]

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [block["total"][0]["surface"] for block in graph["blocks"]] == ["120", "240"]
    assert graph["arithmetic_status"] == "CORROBORATED_STACKED_REQUIRED_TARGET_POPULATIONS"


def test_owner_continuation_allows_one_edit_but_rejects_arbitrary_suffix() -> None:
    records = _stacked_records()
    records[0] = _record("Rủi ro tín dụng (liếp theo)", 40, 20, width=300)
    records.insert(5, _record("Cột tài sản khác", 780, 140, width=120))

    accepted = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert accepted["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    assert (
        accepted["graphs"][0]["owner_context"]["match_kind"]
        == "BOUNDED_ONE_EDIT_CONTINUATION_SUFFIX"
    )

    records[0] = _record("Rủi ro tín dụng (doanh nghiệp khác)", 40, 20, width=360)
    rejected = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert rejected["status"] == "CANDIDATES_NUMERIC_OR_CONTEXT_UNRESOLVED"
    assert rejected["graphs"][0]["owner_context"] is None
    assert "LOAN_QUALITY_OWNER_NOT_RESOLVED" in rejected["graphs"][0]["unresolved_reasons"]


def test_joint_monotone_rows_do_not_shift_over_an_included_disclosure() -> None:
    records = _ordinary_records()
    doubtful_label = next(record for record in records if record["vietocr_text"] == "Nợ nghi ngờ")
    doubtful_label["bbox"] = [100, 320, 410, 352]
    records[9]["bbox"] = [100, 230, 410, 272]
    records[10]["bbox"] = [550, 220, 670, 250]
    records[11]["bbox"] = [850, 220, 970, 250]
    records[9:9] = [
        _record("Trong đó các khoản cho vay tại công ty chứng khoán", 100, 200, width=420),
        _record("7", 550, 197, height=30, width=120),
        _record("6", 850, 197, height=30, width=120),
    ]

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [value["surface"] for value in graph["rows"][1]["values"]] == ["10", "9"]
    included = [
        row
        for row in graph["nonadditive_rows"]
        if row["classification"] == "NONADDITIVE_INCLUDED_DISCLOSURE"
    ]
    assert len(included) == 1
    assert [value["surface"] for value in included[0]["values"]] == ["7", "6"]


def test_total_baseline_may_overlap_tall_loss_label_without_becoming_loss_values() -> None:
    records = _ordinary_records()
    records[-3]["bbox"] = [550, 370, 670, 400]
    records[-2]["bbox"] = [850, 370, 970, 400]

    result = quality.build_loan_quality_variant_graph_document_v2([_page(records)])

    assert result["status"] == "ACCEPTED_UNIQUE_VARIANT_GRAPH"
    graph = result["graphs"][0]
    assert [value["surface"] for value in graph["rows"][-1]["values"]] == ["2", "1"]
    assert [value["surface"] for value in graph["totals"]["core"]] == ["120", "106"]
