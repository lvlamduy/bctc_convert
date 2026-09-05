from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonInvestmentSecuritiesFamilyV1Error,
    _corroborate_identical,
    _equation,
    _neutral_investment_leaf_fingerprint,
    _select_unscoped_closing_equation,
    _source_money,
    build_gemini_json_investment_securities_region_query_receipt_v1,
    coalesce_gemini_json_investment_securities_document_v1,
    compile_gemini_json_investment_securities_family_specs_v1,
    evaluate_gemini_json_investment_securities_family_cluster_v1,
    validate_gemini_json_investment_securities_family_candidate_replay_v1,
)
from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
    _record as _value_record,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "b" * 64
SOURCE_SHA256 = "c" * 64


def _json(name: str) -> dict:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict:
    return compile_gemini_json_investment_securities_family_specs_v1(
        _json("tm-investment-securities-topology-v1.json"),
        _json("tm-investment-securities-evaluation-v1.json"),
        _json("tm-investment-securities-schema-binding-v1.json"),
    )


def _columns() -> list[dict]:
    return [
        {"header_path_exact": ["31/12/2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["31/12/2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]


def _row(
    label: str | None,
    values: list[str | None],
    *,
    hierarchy: list[str | None] | None = None,
    kind: str = "ITEM",
) -> dict:
    return {
        "hierarchy_path_exact": [label] if hierarchy is None else hierarchy,
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(title: str | None, rows: list[dict], *, unit: str = "Triệu đồng") -> dict:
    return {
        "columns": _columns(),
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _section(title: str, *tables: dict, narratives: list[str] | None = None) -> dict:
    return {
        "content_kind": "FINANCIAL_NOTE",
        "narratives_exact": [] if narratives is None else narratives,
        "statement_type": "NOT_APPLICABLE",
        "tables": list(tables),
        "title_exact": title,
    }


def _afs_rows(*, group: bool = True, foreign: bool = False) -> list[dict]:
    branch = "Chứng khoán đầu tư sẵn sàng để bán"
    rows = []
    if group:
        rows.append(
            _row(
                "Chứng khoán nợ",
                ["30", "25"],
                hierarchy=[branch, "Chứng khoán nợ"],
                kind="SUBTOTAL",
            )
        )
    rows.extend(
        [
            _row(
                "Trái phiếu Chính phủ",
                ["10", "8"],
                hierarchy=[branch, "Chứng khoán nợ", "Trái phiếu Chính phủ"],
            ),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["20", "17"],
                hierarchy=[
                    branch,
                    "Chứng khoán nợ",
                    "Chứng khoán nợ do các TCTD khác phát hành",
                ],
            ),
        ]
    )
    if foreign:
        rows.append(
            _row("Khoản mục ngoại lai", ["7", "6"], hierarchy=[branch, "Khoản mục ngoại lai"])
        )
    rows.extend(
        [
            _row(None, ["30", "25"], hierarchy=[branch, None], kind="SUBTOTAL"),
            _row(
                "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
                ["(2)", "(1)"],
                hierarchy=["Dự phòng rủi ro chứng khoán sẵn sàng để bán"],
            ),
            _row(None, ["28", "24"], hierarchy=[None], kind="TOTAL"),
        ]
    )
    return rows


def _htm_rows(*, anonymous_net_under_provision: bool = False) -> list[dict]:
    branch = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    provision = "Dự phòng chứng khoán đầu tư giữ đến ngày đáo hạn"
    net_hierarchy = [provision, None] if anonymous_net_under_provision else [None]
    return [
        _row("Chứng khoán nợ", ["10", "9"], hierarchy=[branch, "Chứng khoán nợ"], kind="SUBTOTAL"),
        _row(
            "Trái phiếu Chính phủ",
            ["4", "3"],
            hierarchy=[branch, "Chứng khoán nợ", "Trái phiếu Chính phủ"],
        ),
        _row(
            "Chứng khoán nợ do các TCTD khác phát hành",
            ["6", "6"],
            hierarchy=[branch, "Chứng khoán nợ", "Chứng khoán nợ do các TCTD khác phát hành"],
        ),
        _row(None, ["10", "9"], hierarchy=[branch, None], kind="SUBTOTAL"),
        _row(provision, ["(2)", "(2)"], hierarchy=[provision]),
        _row("Dự phòng chung", ["(1)", "(1)"], hierarchy=[provision, "Dự phòng chung"]),
        _row("Dự phòng cụ thể", ["(1)", "(1)"], hierarchy=[provision, "Dự phòng cụ thể"]),
        _row(None, ["8", "7"], hierarchy=net_hierarchy, kind="TOTAL"),
    ]


def _base_page(
    *, afs_group: bool = True, foreign: bool = False, anonymous_net: bool = False
) -> dict:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                "Chứng khoán đầu tư sẵn sàng để bán",
                _table(None, _afs_rows(group=afs_group, foreign=foreign)),
            ),
            _section(
                "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                _table(None, _htm_rows(anonymous_net_under_provision=anonymous_net)),
            ),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict, ordinal: int = 1) -> dict:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": "gfpstorev1:json:" + f"{ordinal:064x}",
        "physical_page": ordinal,
        "selected_page_ordinal": ordinal,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _evaluate(page: dict) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    record = _record(page)
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[record], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_investment_securities_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_investment_securities_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={record["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, cluster, candidate


def _evaluate_pages(pages: list[dict]) -> tuple[dict, dict, dict]:
    compiled = _compiled()
    records = [_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)]
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=records, compiled_specs=compiled
    )
    assert cluster["status"] == READY
    receipt = build_gemini_json_investment_securities_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_investment_securities_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={
            record["page_json_version_id"]: record["page_json"] for record in records
        },
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    return compiled, cluster, candidate


def test_exact_multi_component_snapshot_maps_only_schema_roles() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert candidate["closure_receipt"]["structural_root_receipt"]["emitted_mapping"] is False
    assert [cell["coefficient"] for cell in by_role["AFS_DEBT"]["values"]] == [30, 25]
    assert [cell["coefficient"] for cell in by_role["AFS_TOTAL"]["values"]] == [30, 25]
    assert [cell["coefficient"] for cell in by_role["HTM_TOTAL"]["values"]] == [10, 9]
    assert all(
        equation["status"] == "EXACT" for equation in candidate["closure_receipt"]["equations"]
    )


def test_missing_single_group_parent_is_derived_only_from_visible_exact_total() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page(afs_group=False))
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["AFS_DEBT"]["state"] == (
        "DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL"
    )
    assert any(
        equation["equation_kind"] == "DERIVED_EXACT_SINGLE_GROUP_PARENT_FROM_VISIBLE_BRANCH_TOTAL"
        for equation in candidate["closure_receipt"]["equations"]
    )


def test_absolute_and_source_signed_provision_presentations_corroborate() -> None:
    page = _base_page()
    page["sections"].append(
        _section(
            "Dự phòng rủi ro chứng khoán đầu tư",
            _table(
                None,
                [
                    _row("Chứng khoán đầu tư sẵn sàng để bán", ["2", "1"]),
                    _row("Chứng khoán đầu tư giữ đến ngày đáo hạn", ["2", "2"]),
                    _row(None, ["4", "3"], kind="TOTAL", hierarchy=[None]),
                ],
            ),
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["AFS_PROVISION"]["values"]] == [-2, -1]
    assert by_role["AFS_PROVISION"]["state"] == (
        "CORROBORATED_ABSOLUTE_AND_SOURCE_SIGNED_PROVISION_ROWS"
    )


def test_complete_duplicate_corroborates_compatible_partial_source_lanes() -> None:
    partial = _value_record(
        "VAMC_PROVISION",
        [
            {"coefficient": -31, "source_text": "(31)", "state": "RAW_SIGNED_INTEGER"},
            {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
        ],
        [{"row_id": "partial"}],
        "SOURCE_OBSERVED_ROW",
    )
    complete = _value_record(
        "VAMC_PROVISION",
        [
            {"coefficient": -31, "source_text": "(31)", "state": "RAW_SIGNED_INTEGER"},
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        ],
        [{"row_id": "complete"}],
        "SOURCE_OBSERVED_ROW",
    )

    corroborated = _corroborate_identical("VAMC_PROVISION", [partial, complete])

    assert corroborated is not None
    assert [cell["coefficient"] for cell in corroborated["cells"]] == [-31, 0]
    assert corroborated["state"] == (
        "CORROBORATED_COMPLETE_SOURCE_ROW_WITH_COMPATIBLE_PARTIAL_PRESENTATIONS"
    )
    assert corroborated["source_refs"] == [{"row_id": "partial"}, {"row_id": "complete"}]


def test_partial_duplicate_corroboration_requires_one_nonconflicting_complete_row() -> None:
    left = _value_record(
        "VAMC_PROVISION",
        [
            {"coefficient": -31, "source_text": "(31)", "state": "RAW_SIGNED_INTEGER"},
            {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
        ],
        [{"row_id": "left"}],
        "SOURCE_OBSERVED_ROW",
    )
    complementary = _value_record(
        "VAMC_PROVISION",
        [
            {"coefficient": None, "source_text": None, "state": "BLANK_SOURCE_CELL"},
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        ],
        [{"row_id": "right"}],
        "SOURCE_OBSERVED_ROW",
    )
    conflicting = copy.deepcopy(complementary)
    conflicting["cells"][0] = {
        "coefficient": -30,
        "source_text": "(30)",
        "state": "RAW_SIGNED_INTEGER",
    }

    assert _corroborate_identical("VAMC_PROVISION", [left, complementary]) is None
    assert _corroborate_identical("VAMC_PROVISION", [left, conflicting]) is None


def test_anonymous_subtotal_under_provision_is_bound_by_net_equation_not_hierarchy() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_base_page(anonymous_net=True))
    assert candidate["status"] == READY
    assert not any(
        reason.startswith("PARENT_CHILD_EQUATION_MISMATCH") for reason in candidate["reasons"]
    )
    assert any(
        equation["equation_kind"].startswith("EXACT_VISIBLE_NET_TOTAL")
        and equation["result_role"] == "HTM_TOTAL"
        for equation in candidate["closure_receipt"]["equations"]
    )


def test_combined_afs_htm_vamc_controls_close_only_against_complete_frontiers() -> None:
    page = _base_page()
    page["sections"].extend(
        [
            _section(
                "Trái phiếu đặc biệt do VAMC phát hành",
                _table(
                    None,
                    [
                        _row("Mệnh giá trái phiếu đặc biệt", ["3", "3"]),
                        _row("Dự phòng trái phiếu đặc biệt", ["(1)", "(1)"]),
                        _row(None, ["2", "2"], kind="TOTAL", hierarchy=[None]),
                    ],
                ),
            ),
            _section(
                "Chứng khoán đầu tư",
                _table(
                    None,
                    [
                        _row(None, ["43", "37"], kind="TOTAL", hierarchy=[None]),
                        _row("Chứng khoán đầu tư sẵn sàng để bán", ["30", "25"]),
                        _row("Chứng khoán đầu tư giữ đến ngày đáo hạn", ["10", "9"]),
                        _row("Trái phiếu đặc biệt do VAMC phát hành", ["3", "3"]),
                        _row(None, ["(5)", "(4)"], kind="TOTAL", hierarchy=[None]),
                        _row(
                            "Dự phòng rủi ro chứng khoán sẵn sàng để bán",
                            ["(2)", "(1)"],
                        ),
                        _row(
                            "Dự phòng chứng khoán đầu tư giữ đến ngày đáo hạn",
                            ["(2)", "(2)"],
                        ),
                        _row("Dự phòng trái phiếu đặc biệt", ["(1)", "(1)"]),
                        _row(None, ["38", "33"], kind="TOTAL", hierarchy=[None]),
                    ],
                ),
            ),
        ]
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    kinds = {equation["equation_kind"] for equation in candidate["closure_receipt"]["equations"]}
    assert any("COMBINED_AFS_GROSS_HTM_GROSS_VAMC_GROSS" in kind for kind in kinds)
    assert any("COMBINED_AFS_HTM_VAMC_PROVISIONS_SOURCE_SIGNED" in kind for kind in kinds)
    assert any("VAMC_NET_WITH_SOURCE_SIGNED_PROVISION" in kind for kind in kinds)


def test_unbound_money_row_in_declared_table_fails_closed() -> None:
    page = _base_page(foreign=True)
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNUSABLE_DECLARED_ROLE_TABLE_IN_SELECTED_DOCUMENT" in cluster["reasons"]
    assert cluster["component_regions"] == []


def test_quality_blank_is_omitted_even_when_visible_total_closes_both_lanes() -> None:
    page = _base_page()
    page["sections"].append(
        _section(
            "Phân tích chất lượng chứng khoán được phân loại là tài sản có rủi ro tín dụng",
            _table(
                None,
                [
                    _row("Nợ đủ tiêu chuẩn", ["10", "9"]),
                    _row("Nợ cần chú ý", [None, None]),
                    _row(None, ["10", "9"], kind="TOTAL", hierarchy=[None]),
                ],
            ),
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert "QUALITY_WATCH" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    omissions = candidate["closure_receipt"]["source_visible_blank_value_omissions"]
    assert [(item["role"], item["blank_lanes"]) for item in omissions] == [
        ("QUALITY_WATCH", [1, 2])
    ]
    quality_equation = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"] == "EXACT_VISIBLE_QUALITY_ROWS_EQUAL_SOURCE_TOTAL"
    )
    assert quality_equation["status"] == "EXACT"
    assert quality_equation["component_roles"] == ["QUALITY_STANDARD"]


def test_quality_blank_remains_unresolved_when_visible_total_does_not_close() -> None:
    page = _base_page()
    page["sections"].append(
        _section(
            "Phân tích chất lượng chứng khoán được phân loại là tài sản có rủi ro tín dụng",
            _table(
                None,
                [
                    _row("Nợ đủ tiêu chuẩn", ["10", "9"]),
                    _row("Nợ cần chú ý", [None, None]),
                    _row(None, ["11", "9"], kind="TOTAL", hierarchy=[None]),
                ],
            ),
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert "QUALITY_VISIBLE_TOTAL_DOES_NOT_CLOSE_ROLE_FRONTIER" in candidate["reasons"]
    assert candidate["mappings"] == []


def test_conflicting_period_dates_in_one_money_column_fail_closed() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "31/12/2025",
        "30/06/2025",
        "Triệu đồng",
    ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("PERIOD" in reason or "DATE" in reason for reason in candidate["reasons"])


def test_conflicting_money_magnitudes_fail_closed() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert any("UNIT" in reason for reason in candidate["reasons"])


def test_movement_and_non_money_rate_views_are_typed_controls_not_components() -> None:
    page = _base_page()
    movement = _table(
        None,
        [
            _row("Dự phòng chung", ["5", "4"]),
            _row("Trích lập dự phòng", ["1", "1"]),
        ],
    )
    rate = {
        "columns": [
            {"header_path_exact": ["31/12/2025", "Lãi suất (%/năm)"], "value_kind": "PERCENT"},
            {"header_path_exact": ["31/12/2024", "Lãi suất (%/năm)"], "value_kind": "PERCENT"},
        ],
        "continuation": "NONE",
        "rows": [
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["7,1%", "6,8%"],
                hierarchy=[
                    "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                    "Chứng khoán nợ do các TCTD khác phát hành",
                ],
            )
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    page["sections"].extend(
        [
            _section(
                "Chi phí dự phòng rủi ro tín dụng cho chứng khoán đầu tư giữ đến ngày đáo hạn",
                movement,
            ),
            _section("Chứng khoán đầu tư giữ đến ngày đáo hạn", rate),
        ]
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    dispositions = {
        item["classification"]["disposition"] for item in cluster["declared_role_table_inventory"]
    }
    assert candidate["status"] == READY
    assert "EXCLUDED_TYPED_CONTROL:PROVISION_MOVEMENT" in dispositions
    assert "EXCLUDED_TYPED_CONTROL:INTEREST_RATE_OR_PERCENTAGE_VIEW" in dispositions


def test_reset_requires_a_new_source_visible_owner_before_later_component() -> None:
    page = _base_page()
    afs = page["sections"][0]["tables"][0]
    page["sections"] = [
        _section("Chứng khoán đầu tư"),
        _section("Góp vốn, đầu tư dài hạn"),
        _section("Chi tiết", afs),
    ]
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "COMPONENT_CROSSES_RESET_WITHOUT_LOCAL_OWNER" in cluster["reasons"]


def test_candidate_replay_rejects_coherent_source_receipt_drift() -> None:
    compiled, cluster, candidate = _evaluate(_base_page())
    forged = copy.deepcopy(candidate)
    forged["closure_receipt"]["table_receipts"][0]["classification"]["role_hits"][0]["role"] = (
        "AFS_EQUITY"
    )
    with pytest.raises(
        GeminiJsonInvestmentSecuritiesFamilyV1Error,
        match="candidate does not replay exactly",
    ):
        validate_gemini_json_investment_securities_family_candidate_replay_v1(
            forged,
            regions=cluster["component_regions"],
            page_json_by_version={_record(_base_page())["page_json_version_id"]: _base_page()},
            compiled_specs=compiled,
            query_receipt=build_gemini_json_investment_securities_region_query_receipt_v1(
                cluster["component_regions"]
            ),
        )


def test_million_vnd_rounding_closure_is_bounded_and_never_used_for_one_visible_item() -> None:
    components = [
        _value_record(
            "AFS_DEBT_GOVERNMENT",
            [
                {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
                {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
            ],
            [],
            "SOURCE_OBSERVED_ROW",
        ),
        _value_record(
            "AFS_DEBT_CREDIT_INSTITUTIONS",
            [
                {"coefficient": 20, "source_text": "20", "state": "SOURCE_NUMERIC"},
                {"coefficient": 17, "source_text": "17", "state": "SOURCE_NUMERIC"},
            ],
            [],
            "SOURCE_OBSERVED_ROW",
        ),
    ]

    def total(current: int, comparative: int) -> dict:
        return _value_record(
            "AFS_TOTAL",
            [
                {
                    "coefficient": current,
                    "source_text": str(current),
                    "state": "SOURCE_NUMERIC",
                },
                {
                    "coefficient": comparative,
                    "source_text": str(comparative),
                    "state": "SOURCE_NUMERIC",
                },
            ],
            [],
            "SOURCE_OBSERVED_ROW",
        )

    rounded = _equation(
        equation_kind="TEST",
        components=components,
        result=total(31, 25),
        canonical_unit="MILLION_VND",
    )
    assert rounded["status"] == "EXACT_WITHIN_ONE_MILLION_VND_ROUNDING"
    assert rounded["precision_receipt"]["observed_deltas"] == [-1, 0]
    assert (
        _equation(
            equation_kind="TEST",
            components=components,
            result=total(32, 25),
            canonical_unit="MILLION_VND",
        )["status"]
        == "MISMATCH"
    )
    assert (
        _equation(
            equation_kind="TEST",
            components=components,
            result=total(31, 25),
            canonical_unit="VND",
        )["status"]
        == "MISMATCH"
    )
    assert (
        _equation(
            equation_kind="TEST",
            components=components[:1],
            result=total(11, 8),
            canonical_unit="MILLION_VND",
        )["status"]
        == "MISMATCH"
    )


def test_non_latin_dash_annotation_is_conditional_not_silent_numeric_coercion() -> None:
    assert _source_money("-单") == {
        "coefficient": 0,
        "source_text": "-单",
        "state": "ANNOTATED_DASH_ZERO_IF_EQUATION_EXACT",
    }
    with pytest.raises(ValueError):
        _source_money("ABC-")


def _repeated_summary_page(*, mismatch_detail: bool = False) -> dict:
    afs = "Chứng khoán đầu tư sẵn sàng để bán"
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    summary = _table(
        "Chứng khoán đầu tư",
        [
            _row(afs, ["30", "25"], hierarchy=[afs], kind="GROUP"),
            _row("Trái phiếu Chính phủ", ["10", "8"], hierarchy=[afs, "Chứng khoán nợ"]),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["20", "17"],
                hierarchy=[afs, "Chứng khoán nợ"],
            ),
            _row(htm, ["10", "9"], hierarchy=[htm], kind="GROUP"),
            _row("Trái phiếu Chính phủ", ["4", "3"], hierarchy=[htm, "Chứng khoán nợ"]),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["6", "6"],
                hierarchy=[htm, "Chứng khoán nợ"],
            ),
            _row(None, ["40", "34"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    afs_detail = _table(
        None,
        [
            _row("Trái phiếu Chính phủ", ["10", "8"], hierarchy=[afs, "Chứng khoán nợ"]),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["21" if mismatch_detail else "20", "17"],
                hierarchy=[afs, "Chứng khoán nợ"],
            ),
            _row(None, ["30", "25"], hierarchy=[afs, None], kind="TOTAL"),
        ],
    )
    htm_detail = _table(
        None,
        [
            _row("Trái phiếu Chính phủ", ["4", "3"], hierarchy=[htm, "Chứng khoán nợ"]),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["6", "6"],
                hierarchy=[htm, "Chứng khoán nợ"],
            ),
            _row(None, ["10", "9"], hierarchy=[htm, None], kind="TOTAL"),
        ],
    )
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section("Chứng khoán đầu tư", summary),
            _section(afs, afs_detail),
            _section(htm, htm_detail),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def test_exact_repeated_detail_views_are_excluded_without_double_counting() -> None:
    _compiled_specs, cluster, candidate = _evaluate(_repeated_summary_page())
    dispositions = [item["disposition"] for item in cluster["declared_role_table_inventory"]]
    assert candidate["status"] == READY
    assert dispositions.count("EXCLUDED_EXACT_REPEATED_DETAIL_VIEW") == 2
    assert len(cluster["component_regions"]) == 1


def test_repeated_detail_fingerprint_orders_observed_and_blank_lanes() -> None:
    item = {
        "classification": {
            "money_column_ordinals": [1, 2],
            "role_hits": [
                {"role": "AFS_DEBT_GOVERNMENT", "row_ordinal": 1},
                {"role": "AFS_DEBT_GOVERNMENT", "row_ordinal": 2},
            ],
        },
        "compiled_specs": _compiled(),
        "table": _table(
            "Chứng khoán đầu tư sẵn sàng để bán",
            [
                _row("Trái phiếu Chính phủ", ["10", "8"]),
                _row("Trái phiếu Chính phủ", [None, "8"]),
            ],
        ),
    }

    assert _neutral_investment_leaf_fingerprint(item) == (
        ("DEBT_GOVERNMENT", (10, 8)),
        ("DEBT_GOVERNMENT", (None, 8)),
    )


def test_nonidentical_detail_view_is_never_excluded_as_a_repeat() -> None:
    page = _repeated_summary_page(mismatch_detail=True)
    compiled = _compiled()
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert not any(
        item["disposition"] == "EXCLUDED_EXACT_REPEATED_DETAIL_VIEW"
        for item in cluster["declared_role_table_inventory"]
    )
    receipt = build_gemini_json_investment_securities_region_query_receipt_v1(
        cluster["component_regions"]
    )
    candidate = evaluate_gemini_json_investment_securities_family_cluster_v1(
        regions=cluster["component_regions"],
        page_json_by_version={_record(page)["page_json_version_id"]: page},
        compiled_specs=compiled,
        query_receipt=receipt,
    )
    assert candidate["status"] == UNRESOLVED


def _label_shift_page(*, debt_subtotal: str = "10") -> dict:
    page = _base_page()
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    provision = "Dự phòng rủi ro chứng khoán đầu tư giữ đến ngày đáo hạn"
    page["sections"][1]["tables"][0]["rows"] = [
        _row("Trái phiếu Chính phủ", ["4", "3"], hierarchy=[htm, "Chứng khoán nợ"]),
        _row(
            "Chứng khoán nợ do các TCTD khác phát hành",
            ["6", "6"],
            hierarchy=[htm, "Chứng khoán nợ"],
        ),
        _row(provision, [debt_subtotal, "9"], hierarchy=[provision], kind="GROUP"),
        _row(provision, ["(2)", "(2)"], hierarchy=[provision]),
        _row("Dự phòng giảm giá", ["-", "-"], hierarchy=[provision, "Dự phòng giảm giá"]),
        _row("Dự phòng chung", ["(2)", "(2)"], hierarchy=[provision, "Dự phòng chung"]),
        _row("Dự phòng cụ thể", ["-", "-"], hierarchy=[provision, "Dự phòng cụ thể"]),
        _row(None, ["8", "7"], hierarchy=[None], kind="TOTAL"),
    ]
    return page


def test_exact_debt_and_provision_frontiers_reclassify_shifted_source_label() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_label_shift_page())
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert by_role["HTM_DEBT"]["state"] == (
        "SOURCE_ROW_RECLASSIFIED_BY_EXACT_DEBT_AND_PROVISION_FRONTIERS"
    )
    assert len(candidate["closure_receipt"]["source_row_reclassifications"]) == 1


def test_shifted_source_label_without_exact_debt_frontier_remains_unresolved() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_label_shift_page(debt_subtotal="11"))
    assert candidate["status"] == UNRESOLVED
    assert candidate["closure_receipt"]["source_row_reclassifications"] == []


def _adjacent_blank_stub_pages(*, source_value: str | None = None) -> list[dict]:
    first = _base_page()
    first["sections"] = first["sections"][:1]
    stub = {
        "columns": [{"header_path_exact": [None], "value_kind": "MONEY"}],
        "continuation": "CONTINUES_ON_NEXT_PAGE",
        "rows": [
            _row(
                "Trái phiếu Chính phủ",
                [source_value],
                hierarchy=["Chứng khoán đầu tư giữ đến ngày đáo hạn", "Chứng khoán nợ"],
            )
        ],
        "title_exact": "Chứng khoán đầu tư giữ đến ngày đáo hạn",
        "unit_exact": "Triệu đồng",
    }
    first["sections"].append(_section("Chứng khoán đầu tư giữ đến ngày đáo hạn", stub))
    continuation = _table(
        None,
        [
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                [None, None],
                hierarchy=["Chứng khoán đầu tư giữ đến ngày đáo hạn", "Chứng khoán nợ"],
            ),
            _row(
                "Chứng khoán nợ do các TCKT trong nước phát hành",
                [None, None],
                hierarchy=["Chứng khoán đầu tư giữ đến ngày đáo hạn", "Chứng khoán nợ"],
            ),
            _row(None, ["-", "-"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    continuation["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    second = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [_section("Chứng khoán đầu tư giữ đến ngày đáo hạn", continuation)],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    return [first, second]


def test_adjacent_single_lane_blank_stub_is_receipted_but_never_mapped() -> None:
    _compiled_specs, cluster, candidate = _evaluate_pages(_adjacent_blank_stub_pages())
    assert candidate["status"] == READY
    assert any("single_lane_blank_projection" in region for region in cluster["component_regions"])
    assert "HTM_DEBT_GOVERNMENT" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    omissions = candidate["closure_receipt"]["source_visible_blank_value_omissions"]
    government = next(item for item in omissions if item["role"] == "HTM_DEBT_GOVERNMENT")
    assert government["blank_lanes"] == [1, 2]
    assert government["disposition"] == "SOURCE_VISIBLE_ALL_BLANK_NO_VALUE_OBSERVATION"


def test_nonblank_single_lane_stub_is_not_projected() -> None:
    pages = _adjacent_blank_stub_pages(source_value="1")
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNUSABLE_DECLARED_ROLE_TABLE_IN_SELECTED_DOCUMENT" in cluster["reasons"]
    assert cluster["component_regions"] == []


def test_blank_stub_does_not_block_a_distinct_visible_total_observation() -> None:
    pages = _adjacent_blank_stub_pages()
    pages[1]["sections"][0]["tables"][0]["rows"][-1]["values_exact"] = ["1", "-"]
    _compiled_specs, _cluster, candidate = _evaluate_pages(pages)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert "HTM_DEBT_GOVERNMENT" not in by_role
    assert [cell["coefficient"] for cell in by_role["HTM_TOTAL"]["values"]] == [1, 0]
    assert by_role["HTM_TOTAL"]["values"][1]["state"] == "DASH_ZERO"


def test_blank_stub_without_exact_continuation_markers_is_not_projected() -> None:
    pages = _adjacent_blank_stub_pages()
    pages[1]["sections"][0]["tables"][0]["continuation"] = "NONE"
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)],
        compiled_specs=_compiled(),
    )
    assert cluster["status"] == UNRESOLVED
    assert not any(
        "single_lane_blank_projection" in region for region in cluster["component_regions"]
    )


def _split_group_caption_pages(*, continuation_head: str = "hạn") -> list[dict]:
    first = _base_page()
    first["sections"] = first["sections"][:1]
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    first_half = _table(
        htm,
        [
            _row("Trái phiếu Chính phủ", ["4", "3"], hierarchy=[htm, "Chứng khoán nợ"]),
            _row(
                "Chứng khoán nợ do các TCTD khác phát hành",
                ["6", "6"],
                hierarchy=[htm, "Chứng khoán nợ"],
            ),
            _row(
                "Dự phòng rủi ro chứng khoán giữ đến ngày đáo",
                [None, None],
                hierarchy=["Dự phòng rủi ro chứng khoán giữ đến ngày đáo"],
                kind="GROUP",
            ),
        ],
    )
    first_half["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    first["sections"].append(_section(htm, first_half))
    second_half = _table(
        None,
        [
            _row(continuation_head, [None, None]),
            _row("Dự phòng giảm giá", ["-", "-"]),
            _row("Dự phòng chung", ["-", "-"]),
            _row("Dự phòng cụ thể", [None, None]),
            _row(None, ["10", "9"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    second_half["continuation"] = "CONTINUES_FROM_PREVIOUS_PAGE"
    second = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [_section("Chi tiết tiếp theo", second_half)],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    return [first, second]


def test_group_caption_split_at_page_boundary_recovers_only_exact_declared_parent() -> None:
    _compiled_specs, cluster, candidate = _evaluate_pages(_split_group_caption_pages())
    continuation = next(
        region for region in cluster["component_regions"] if region["physical_page"] == 2
    )
    assert continuation["continuation_parent_roles"] == ["HTM_PROVISION"]
    assert candidate["status"] == READY


def test_nonmatching_group_caption_fragments_do_not_create_a_parent() -> None:
    pages = _split_group_caption_pages(continuation_head="khác")
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page, ordinal) for ordinal, page in enumerate(pages, start=1)],
        compiled_specs=_compiled(),
    )
    assert all(region["physical_page"] == 1 for region in cluster["component_regions"])
    assert not any(
        region["continuation_parent_roles"] == ["HTM_PROVISION"]
        for region in cluster["component_regions"]
    )


def test_vnd_unit_is_preserved_and_missing_or_mixed_unit_fails_closed() -> None:
    vnd_page = _base_page()
    for section in vnd_page["sections"]:
        table = section["tables"][0]
        table["unit_exact"] = "VND"
        for column in table["columns"]:
            column["header_path_exact"] = [column["header_path_exact"][0]]
    _compiled_specs, _cluster, candidate = _evaluate(vnd_page)
    assert candidate["status"] == READY
    assert {mapping["unit"] for mapping in candidate["mappings"]} == {"VND"}

    missing = copy.deepcopy(vnd_page)
    for section in missing["sections"]:
        section["tables"][0]["unit_exact"] = None
    _compiled_specs, _cluster, missing_candidate = _evaluate(missing)
    assert missing_candidate["status"] == UNRESOLVED
    assert any("UNIT" in reason for reason in missing_candidate["reasons"])

    mixed = copy.deepcopy(vnd_page)
    mixed["sections"][1]["tables"][0]["unit_exact"] = "Triệu đồng"
    _compiled_specs, _cluster, mixed_candidate = _evaluate(mixed)
    assert mixed_candidate["status"] == UNRESOLVED
    assert "COMPONENT_MONEY_UNITS_DIFFER" in mixed_candidate["reasons"]


def test_literal_backslash_n_header_is_projected_before_period_and_unit_binding() -> None:
    page = _base_page()
    for section in page["sections"]:
        table = section["tables"][0]
        table["columns"][0]["header_path_exact"] = [
            r"Ngày 31 tháng 12\nnăm 2025\nTriệu đồng"
        ]
        table["columns"][1]["header_path_exact"] = [
            r"Ngày 31 tháng 12\nnăm 2024\nTriệu đồng"
        ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["table_receipts"]
    assert all(
        receipt["unit_axis"]["canonical_unit"] == "MILLION_VND" for receipt in receipts
    )
    assert all(
        receipt["serialized_header_linebreak_projection_receipt"]["rule"]
        == "LITERAL_BACKSLASH_N_IN_COLUMN_HEADER_TO_VISUAL_LINE_BREAK"
        for receipt in receipts
    )


def test_exact_trong_do_decomposition_is_source_only_below_one_schema_leaf() -> None:
    page = _base_page()
    rows = page["sections"][1]["tables"][0]["rows"]
    rows[3:3] = [
        _row(
            "Trái phiếu do các TCTD khác trong nước phát hành",
            ["1", "2"],
            hierarchy=["Trong đó:", "Trái phiếu do các TCTD khác trong nước phát hành"],
        ),
        _row(
            "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
            ["5", "4"],
            hierarchy=[
                "Trong đó:",
                "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
            ],
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    htm_receipt = next(
        receipt
        for receipt in candidate["closure_receipt"]["table_receipts"]
        if receipt["classification"]["component_roles"] == ["HTM"]
    )
    exact_details = [
        row
        for row in htm_receipt["classification"]["source_only_rows"]
        if row["disposition"]
        == "SOURCE_ONLY_EXACT_DETAIL_DECOMPOSITION_OF_MAPPED_SCHEMA_LEAF"
    ]
    assert [(row["owner_role"], row["row_ordinal"]) for row in exact_details] == [
        ("HTM_DEBT_CREDIT_INSTITUTIONS", 4),
        ("HTM_DEBT_CREDIT_INSTITUTIONS", 5),
    ]
    assert sum(
        mapping["role"] == "HTM_DEBT_CREDIT_INSTITUTIONS"
        for mapping in candidate["mappings"]
    ) == 1


def test_trong_do_children_are_not_collapsed_when_they_do_not_reconcile() -> None:
    page = _base_page()
    rows = page["sections"][1]["tables"][0]["rows"]
    rows[3:3] = [
        _row(
            "Trái phiếu do các TCTD khác trong nước phát hành",
            ["2", "2"],
            hierarchy=["Trong đó:", "Trái phiếu do các TCTD khác trong nước phát hành"],
        ),
        _row(
            "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
            ["5", "4"],
            hierarchy=[
                "Trong đó:",
                "Chứng chỉ tiền gửi do các TCTD khác trong nước phát hành",
            ],
        ),
    ]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert not any(
        row["disposition"]
        == "SOURCE_ONLY_EXACT_DETAIL_DECOMPOSITION_OF_MAPPED_SCHEMA_LEAF"
        for receipt in candidate["closure_receipt"]["table_receipts"]
        for row in receipt["classification"]["source_only_rows"]
    )


def test_other_long_term_table_is_excluded_inside_flattened_multi_note_section() -> None:
    page = _base_page()
    page["sections"][0]["narratives_exact"] = [
        "10. CHỨNG KHOÁN ĐẦU TƯ",
        "11. GÓP VỐN, ĐẦU TƯ DÀI HẠN",
    ]
    other = _table(
        None,
        [
            _row("Công ty cổ phần khác", ["10", "10"]),
            _row("Dự phòng giảm giá đầu tư dài hạn khác", ["(2)", "(2)"]),
            _row(None, ["8", "8"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    page["sections"][0]["tables"].append(other)
    compiled = _compiled()
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=compiled
    )
    assert cluster["status"] == READY
    excluded = [
        item["disposition"] for item in cluster["declared_role_table_inventory"]
    ]
    assert "EXCLUDED_TYPED_CONTROL:OTHER_LONG_TERM_INVESTMENT_VIEW" in excluded


def test_exact_ktcap_marker_is_conditional_zero_but_arbitrary_latin_is_invalid() -> None:
    page = _base_page()
    afs_rows = page["sections"][0]["tables"][0]["rows"]
    afs_rows[-2]["values_exact"] = ["-ktCap-", "-ktCap"]
    afs_rows[-1]["values_exact"] = ["30", "25"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    provision = next(
        mapping for mapping in candidate["mappings"] if mapping["role"] == "AFS_PROVISION"
    )
    assert [cell["coefficient"] for cell in provision["values"]] == [0, 0]
    assert all(
        cell["state"].startswith("INFERRED_KTCAP_SERIALIZATION_ARTIFACT")
        for cell in provision["values"]
    )
    with pytest.raises(ValueError):
        _source_money("-arbitraryLatin-")


def test_all_zero_sibling_leaves_are_not_reclassified_as_a_trailing_parent() -> None:
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                htm,
                _table(
                    htm,
                    [
                        _row(
                            "Trái phiếu Chính phủ",
                            ["0", "0"],
                            hierarchy=[htm, "Chứng khoán nợ", "Trái phiếu Chính phủ"],
                        ),
                        _row(
                            "Chứng khoán nợ do các TCTD khác phát hành",
                            ["0", "0"],
                            hierarchy=[
                                htm,
                                "Chứng khoán nợ",
                                "Chứng khoán nợ do các TCTD khác phát hành",
                            ],
                        ),
                        _row(
                            "Chứng khoán nợ do các TCKT trong nước phát hành",
                            ["0", "0"],
                            hierarchy=[
                                htm,
                                "Chứng khoán nợ",
                                "Chứng khoán nợ do các TCKT trong nước phát hành",
                            ],
                        ),
                        _row(None, ["0", "0"], hierarchy=[htm, None], kind="TOTAL"),
                    ],
                ),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert {
        "HTM_DEBT_GOVERNMENT",
        "HTM_DEBT_CREDIT_INSTITUTIONS",
        "HTM_DEBT_DOMESTIC_ECONOMIC_ORGANIZATIONS",
    } <= roles


def test_unlabelled_vamc_subtotal_uses_nearest_branch_but_not_later_total() -> None:
    page = _base_page()
    combined = _table(
        "Trái phiếu đặc biệt do VAMC phát hành",
        [
            _row(
                "Dự phòng chứng khoán đầu tư giữ đến ngày đáo hạn",
                [None, None],
                kind="GROUP",
            ),
            _row("Dự phòng giảm giá", ["-", "-"]),
            _row(None, ["0", "0"], hierarchy=[None], kind="SUBTOTAL"),
            _row("Trái phiếu đặc biệt do VAMC phát hành", [None, None], kind="GROUP"),
            _row("Mệnh giá trái phiếu đặc biệt", ["-单", "-单"]),
            _row("Dự phòng trái phiếu đặc biệt", ["-单", "-单"]),
            _row(None, ["0", "0"], hierarchy=[None], kind="SUBTOTAL"),
            _row(None, ["28", "24"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    page["sections"].append(_section("Chi tiết tiếp theo", combined))
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    combined_receipt = candidate["closure_receipt"]["table_receipts"][-1]
    controls = [
        hit["role"]
        for hit in combined_receipt["classification"]["role_hits"]
        if hit["row_ordinal"] in {7, 8}
    ]
    assert controls == ["VAMC_NET_TOTAL_CONTROL", "UNSCOPED_TOTAL_CONTROL"]
    mapped = {mapping["role"] for mapping in candidate["mappings"]}
    assert {"VAMC_FACE_VALUE", "VAMC_PROVISION"} <= mapped


def _blank_htm_government_page(*, total: str | None = None) -> dict:
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    rows = [
        _row(
            "Trái phiếu Chính phủ",
            [None, None],
            hierarchy=[htm, "Chứng khoán nợ", "Trái phiếu Chính phủ"],
        ),
        _row(
            "Chứng khoán nợ do các TCTD khác phát hành",
            ["-", "-"],
            hierarchy=[
                htm,
                "Chứng khoán nợ",
                "Chứng khoán nợ do các TCTD khác phát hành",
            ],
        ),
        _row(
            "Chứng khoán nợ do các TCKT trong nước phát hành",
            ["-", "-"],
            hierarchy=[
                htm,
                "Chứng khoán nợ",
                "Chứng khoán nợ do các TCKT trong nước phát hành",
            ],
        ),
    ]
    if total is not None:
        rows.append(_row(None, [total, total], hierarchy=[htm, None], kind="TOTAL"))
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [_section(htm, _table(htm, rows))],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def test_all_blank_visible_leaf_without_total_is_preserved_as_no_value_observation() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(_blank_htm_government_page())
    assert candidate["status"] == READY
    assert "HTM_DEBT_GOVERNMENT" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    omissions = candidate["closure_receipt"]["source_visible_blank_value_omissions"]
    assert len(omissions) == 1
    assert omissions[0]["role"] == "HTM_DEBT_GOVERNMENT"
    assert omissions[0]["blank_lanes"] == [1, 2]
    assert omissions[0]["disposition"] == (
        "SOURCE_VISIBLE_ALL_BLANK_NO_VALUE_OBSERVATION"
    )
    assert omissions[0]["source_refs"][0]["label_exact"] == "Trái phiếu Chính phủ"


def test_dash_total_does_not_turn_all_blank_visible_leaf_into_zero() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(
        _blank_htm_government_page(total="-")
    )
    assert candidate["status"] == READY
    assert "HTM_DEBT_GOVERNMENT" not in {
        mapping["role"] for mapping in candidate["mappings"]
    }
    omissions = candidate["closure_receipt"]["source_visible_blank_value_omissions"]
    assert [item["role"] for item in omissions] == ["HTM_DEBT_GOVERNMENT"]


def test_exact_parent_closure_never_maps_a_blank_child_as_zero() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(
        _blank_htm_government_page(total="-")
    )
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert "HTM_DEBT_GOVERNMENT" not in by_role
    assert [cell["coefficient"] for cell in by_role["HTM_TOTAL"]["values"]] == [0, 0]
    closing = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "HTM_TOTAL" and equation["status"] == "EXACT"
    ]
    assert len(closing) == 1
    assert "HTM_DEBT_GOVERNMENT" not in closing[0]["component_roles"]


def test_numbered_zero_population_heading_is_not_an_unscoped_total() -> None:
    page = _base_page()
    page["sections"][0]["tables"][0]["rows"].append(
        _row(
            "8.3 Phân tích chất lượng chứng khoán đầu tư được phân loại là tài sản có rủi ro tín dụng",
            ["-", "-"],
            kind="TOTAL",
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipt = candidate["closure_receipt"]["table_receipts"][0]
    assert receipt["classification"]["source_only_rows"][-1] == {
        "disposition": "SOURCE_ONLY_STRUCTURAL_HEADING_WITH_PLACEHOLDER_CELLS",
        "owner_role": "QUALITY_BRANCH",
        "row_ordinal": len(page["sections"][0]["tables"][0]["rows"]),
    }


def test_nonclosing_total_does_not_license_all_blank_visible_leaf() -> None:
    _compiled_specs, _cluster, candidate = _evaluate(
        _blank_htm_government_page(total="1")
    )
    assert candidate["status"] == UNRESOLVED
    assert "HTM_VISIBLE_TOTAL_DOES_NOT_CLOSE_GROSS_OR_NET_FRONTIER" in candidate[
        "reasons"
    ]


def test_partial_blank_visible_leaf_keeps_only_its_observed_lane() -> None:
    page = _blank_htm_government_page(total="-")
    page["sections"][0]["tables"][0]["rows"][0]["values_exact"] = [None, "-"]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["HTM_DEBT_GOVERNMENT"]["values"]] == [
        None,
        0,
    ]
    assert by_role["HTM_DEBT_GOVERNMENT"]["values"][0] == {
        "coefficient": None,
        "source_text": None,
        "state": "BLANK_SOURCE_CELL",
    }
    assert by_role["HTM_DEBT_GOVERNMENT"]["values"][1]["state"] == "DASH_ZERO"
    omissions = candidate["closure_receipt"]["source_visible_blank_value_omissions"]
    assert len(omissions) == 1
    assert omissions[0]["role"] == "HTM_DEBT_GOVERNMENT"
    assert omissions[0]["blank_lanes"] == [1]
    assert omissions[0]["disposition"] == (
        "SOURCE_VISIBLE_PARTIAL_BLANK_LANE_NO_VALUE_OBSERVATION"
    )
    closing = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "HTM_TOTAL"
    )
    assert closing["status"] == "EXACT_OBSERVED_LANES_WITH_BLANK_SOURCE_LANES"
    assert closing["lane_statuses"] == ["UNOBSERVED_SOURCE_LANE", "EXACT"]


def test_owner_qualified_unknown_money_table_is_never_silently_not_observed() -> None:
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                htm,
                _table(htm, [_row("Công cụ nợ hoàn toàn mới", ["3", "2"])]),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNRECOGNIZED_OWNER_QUALIFIED_MONEY_TABLE_IN_SELECTED_DOCUMENT" in cluster[
        "reasons"
    ]


def test_unknown_owner_qualified_sibling_invalidates_an_otherwise_valid_cluster() -> None:
    page = _base_page()
    page["sections"][0]["tables"].append(
        _table(None, [_row("Công cụ nợ hoàn toàn mới", ["3", "2"])])
    )
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == UNRESOLVED
    assert "UNRECOGNIZED_OWNER_QUALIFIED_MONEY_TABLE_IN_SELECTED_DOCUMENT" in cluster[
        "reasons"
    ]


def test_titled_unrelated_money_sibling_does_not_inherit_section_owner() -> None:
    page = _base_page()
    page["sections"][0]["tables"].append(
        _table(
            "25. Lãi thuần từ hoạt động khác",
            [
                _row("Thu về hoạt động kinh doanh khác", ["3", "2"]),
                _row(None, ["3", "2"], hierarchy=[None], kind="TOTAL"),
            ],
        )
    )
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert "UNRECOGNIZED_OWNER_QUALIFIED_MONEY_TABLE_IN_SELECTED_DOCUMENT" not in cluster[
        "reasons"
    ]


def test_trading_activity_table_is_a_typed_exclusion_not_an_unknown_owner_table() -> None:
    page = _base_page()
    title = "24. Lãi/lỗ thuần từ hoạt động kinh doanh (mua bán) chứng khoán đầu tư"
    page["sections"].append(
        _section(
            title,
            _table(
                None,
                [
                    _row("Thu nhập từ mua bán chứng khoán đầu tư", ["3", "2"]),
                    _row("Chi phí mua bán chứng khoán đầu tư", ["(1)", "(1)"]),
                    _row(None, ["2", "1"], hierarchy=[None], kind="TOTAL"),
                ],
            ),
        )
    )
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert any(
        item["disposition"]
        == "EXCLUDED_TYPED_CONTROL:INVESTMENT_SECURITIES_TRADING_ACTIVITY"
        for item in cluster["declared_role_table_inventory"]
    )


def test_maturity_rate_detail_is_a_typed_exclusion() -> None:
    page = _base_page()
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    detail = {
        "columns": [
            {"header_path_exact": ["Ngày đáo hạn"], "value_kind": "TEXT"},
            {"header_path_exact": ["Lãi suất"], "value_kind": "PERCENT"},
            {"header_path_exact": ["Số lượng"], "value_kind": "COUNT"},
            {"header_path_exact": ["Giá trị đầu tư"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Công ty Quản lý tài sản VAMC", ["Năm 2030", "0%", "2", "10"])
        ],
        "title_exact": htm,
        "unit_exact": "Triệu đồng",
    }
    page["sections"].append(_section(htm, detail))
    cluster = coalesce_gemini_json_investment_securities_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )
    assert cluster["status"] == READY
    assert any(
        item["disposition"] == "EXCLUDED_TYPED_CONTROL:INTEREST_RATE_OR_PERCENTAGE_VIEW"
        for item in cluster["declared_role_table_inventory"]
    )


def test_quality_debt_risk_wording_maps_visible_quality_rows() -> None:
    page = _base_page()
    title = (
        "12.3 Phân tích chất lượng chứng khoán nợ được phân loại là tài sản chịu "
        "rủi ro tín dụng theo Thông tư 31"
    )
    page["sections"].append(
        _section(
            title,
            _table(
                title,
                [
                    _row("Nợ đủ tiêu chuẩn", ["5", "4"]),
                    _row("Nợ cần chú ý", ["1", "-"]),
                    _row(None, ["6", "4"], hierarchy=[None], kind="TOTAL"),
                ],
            ),
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert {"QUALITY_STANDARD", "QUALITY_WATCH"} <= roles


def test_numbered_quality_caption_with_dash_and_blank_cells_is_structural() -> None:
    page = _base_page()
    caption = (
        "8.3 Phân tích chất lượng chứng khoán đầu tư được phân loại là tài sản "
        "có rủi ro tín dụng"
    )
    page["sections"][0]["tables"][0]["rows"].append(
        _row(caption, ["-", None], hierarchy=[caption], kind="TOTAL")
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    source_only = [
        item
        for inventory in cluster["declared_role_table_inventory"]
        for item in inventory["classification"]["source_only_rows"]
    ]

    assert candidate["status"] == READY
    assert source_only[-1] == {
        "disposition": "SOURCE_ONLY_STRUCTURAL_HEADING_WITH_PLACEHOLDER_CELLS",
        "owner_role": "QUALITY_BRANCH",
        "row_ordinal": 7,
    }


def test_unnumbered_quality_total_with_blank_lane_is_not_silently_structural() -> None:
    page = _base_page()
    caption = (
        "Phân tích chất lượng chứng khoán đầu tư được phân loại là tài sản có "
        "rủi ro tín dụng"
    )
    page["sections"][0]["tables"][0]["rows"].append(
        _row(caption, ["-", None], hierarchy=[caption], kind="TOTAL")
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)

    assert candidate["status"] == UNRESOLVED
    assert "UNSCOPED_VISIBLE_TOTAL_DOES_NOT_CLOSE_ANY_FAMILY_FRONTIER" in candidate[
        "reasons"
    ]


def test_table_local_htm_owner_overrides_prior_afs_section_narrative() -> None:
    page = _base_page()
    afs_section, htm_section = page["sections"]
    afs_section["title_exact"] = "7. Chứng khoán đầu tư"
    afs_section["narratives_exact"] = ["a. Chứng khoán đầu tư sẵn sàng để bán"]
    htm_table = htm_section["tables"][0]
    htm_table["title_exact"] = "b. Chứng khoán đầu tư giữ đến ngày đáo hạn"
    afs_section["tables"].append(htm_table)
    page["sections"] = [afs_section]
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    assert "HTM_DEBT_GOVERNMENT" in {
        mapping["role"] for mapping in candidate["mappings"]
    }


def test_combined_provision_summary_is_promoted_as_exact_control_evidence() -> None:
    page = _base_page()
    title = "12.3 Dự phòng rủi ro chứng khoán đầu tư"
    page["sections"].append(
        _section(
            title,
            _table(
                title,
                [
                    _row(
                        "Dự phòng rủi ro trái phiếu doanh nghiệp chưa niêm yết",
                        ["(4)", "(3)"],
                    ),
                    _row(None, ["4", "3"], hierarchy=[None], kind="TOTAL"),
                ],
            ),
        )
    )
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert any(region.get("promoted_summary_control") is True for region in cluster["component_regions"])
    assert candidate["status"] == READY
    summary_equations = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_kind"].startswith(
            "EXACT_PROMOTED_SUMMARY_DETAIL_ROWS_EQUAL_TERMINAL_CONTROL"
        )
    ]
    assert len(summary_equations) == 1
    assert summary_equations[0]["status"] == "EXACT"
    assert summary_equations[0]["multipliers"] == [-1]
    receipts = candidate["closure_receipt"]["promoted_summary_resolution_receipts"]
    assert receipts[0]["disposition"] == (
        "SOURCE_ONLY_EXACT_INTERNAL_PROMOTED_SUMMARY_DECOMPOSITION"
    )


def test_promoted_summary_requires_an_exact_internal_terminal_control() -> None:
    page = _base_page()
    title = "12.3 Dự phòng rủi ro chứng khoán đầu tư"
    page["sections"].append(
        _section(
            title,
            _table(
                title,
                [
                    _row(
                        "Dự phòng rủi ro trái phiếu doanh nghiệp chưa niêm yết",
                        ["4", "3"],
                    ),
                    _row(None, ["8", "3"], hierarchy=[None], kind="TOTAL"),
                ],
            ),
        )
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert "UNSCOPED_VISIBLE_TOTAL_DOES_NOT_CLOSE_ANY_FAMILY_FRONTIER" in candidate[
        "reasons"
    ]


def test_exact_afs_htm_quality_slices_reclassify_the_terminal_quality_role() -> None:
    page = _base_page()
    afs_table = page["sections"][0]["tables"][0]
    htm_table = page["sections"][1]["tables"][0]
    quality_table = _table(
        None,
        [
            _row("Nợ đủ tiêu chuẩn", [None, None], kind="GROUP"),
            _row(
                "Chứng khoán đầu tư sẵn sàng để bán",
                ["2", "1"],
                hierarchy=["Nợ đủ tiêu chuẩn", "Chứng khoán đầu tư sẵn sàng để bán"],
            ),
            _row(
                "Chứng khoán đầu tư giữ đến ngày đáo hạn",
                ["3", "4"],
                hierarchy=["Nợ đủ tiêu chuẩn", "Chứng khoán đầu tư giữ đến ngày đáo hạn"],
            ),
            _row(None, ["5", "5"], hierarchy=[None], kind="TOTAL"),
        ],
    )
    section = _section("Chứng khoán đầu tư", afs_table)
    section["tables"].extend([htm_table, quality_table])
    page["sections"] = [section]
    _compiled_specs, cluster, candidate = _evaluate(page)
    assert any(region.get("promoted_summary_control") is True for region in cluster["component_regions"])
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["QUALITY_STANDARD"]["values"]] == [5, 5]
    assert by_role["QUALITY_STANDARD"]["state"] == (
        "SOURCE_TOTAL_RECLASSIFIED_FROM_EXACT_AFS_HTM_QUALITY_SLICES"
    )
    receipts = candidate["closure_receipt"]["promoted_summary_resolution_receipts"]
    assert receipts[0]["disposition"] == (
        "EXACT_QUALITY_ROLE_TOTAL_FROM_AFS_HTM_SLICE_DECOMPOSITION"
    )
    assert receipts[0]["quality_role"] == "QUALITY_STANDARD"


def test_generic_family_total_after_htm_rows_stays_unscoped_and_closes_combined() -> None:
    page = _base_page()
    page["sections"][1]["tables"][0]["rows"].append(
        _row("Tổng chứng khoán đầu tư", ["40", "34"], kind="TOTAL")
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["HTM_TOTAL"]["values"]] == [10, 9]
    family_total = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "UNSCOPED_TOTAL_CONTROL"
        and equation["result_coefficients"] == [40, 34]
    )
    assert family_total["status"] == "EXACT"
    assert {"AFS_DEBT", "HTM_DEBT"} <= set(family_total["component_roles"])


def test_trailing_generic_total_is_reclassified_only_by_exact_combined_frontier() -> None:
    page = _base_page()
    page["sections"][1]["tables"][0]["rows"].append(
        _row("Tổng cộng", ["36", "31"], kind="TOTAL")
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    receipts = candidate["closure_receipt"]["trailing_total_reclassification_receipts"]
    assert len(receipts) == 1
    assert receipts[0]["source_role"] == "HTM_TOTAL"
    assert receipts[0]["disposition"] == (
        "TERMINAL_STRUCTURALLY_COMPREHENSIVE_EXACT_FRONTIER"
    )
    equation = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["equation_id"] == receipts[0]["selected_equation_id"]
    )
    assert equation["equation_kind"].startswith(
        "EXACT_RECLASSIFIED_TRAILING_SOURCE_TOTAL_COMBINED_"
    )
    assert equation["result_coefficients"] == [36, 31]


def test_trailing_generic_total_without_a_combined_frontier_fails_closed() -> None:
    page = _base_page()
    page["sections"][1]["tables"][0]["rows"].append(
        _row("Tổng cộng", ["99", "98"], kind="TOTAL")
    )
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert (
        "TRAILING_VISIBLE_BRANCH_TOTAL_DOES_NOT_CLOSE_LOCAL_OR_COMBINED_FRONTIER"
        in candidate["reasons"]
    )


def test_explicit_trailing_leaf_is_not_reclassified_as_coincident_parent() -> None:
    htm = "Chứng khoán đầu tư giữ đến ngày đáo hạn"
    page = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            _section(
                htm,
                _table(
                    htm,
                    [
                        _row("Trái phiếu Chính phủ", ["10", "10"]),
                        _row(
                            "Chứng khoán nợ do các TCTD khác phát hành",
                            ["20", "20"],
                        ),
                        _row(
                            "Chứng khoán nợ do các TCKT trong nước phát hành",
                            ["30", "30"],
                        ),
                        _row(None, ["60", "60"], hierarchy=[htm, None], kind="TOTAL"),
                    ],
                ),
            )
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _compiled_specs, _cluster, candidate = _evaluate(page)
    assert candidate["status"] == READY
    roles = {mapping["role"] for mapping in candidate["mappings"]}
    assert "HTM_DEBT_DOMESTIC_ECONOMIC_ORGANIZATIONS" in roles
    assert not any(
        mapping["state"] == "SOURCE_ROW_RECLASSIFIED_AS_EXACT_TRAILING_GROUP_AGGREGATE"
        for mapping in candidate["mappings"]
    )


def test_rounding_tolerance_requires_two_nonzero_components_in_each_mismatched_lane() -> None:
    components = [
        _value_record(
            "AFS_DEBT_GOVERNMENT",
            [
                {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
                {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
            ],
            [],
            "SOURCE_OBSERVED_ROW",
        ),
        _value_record(
            "AFS_DEBT_CREDIT_INSTITUTIONS",
            [
                {"coefficient": 20, "source_text": "20", "state": "SOURCE_NUMERIC"},
                {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
            ],
            [],
            "SOURCE_OBSERVED_ROW",
        ),
    ]
    result = _value_record(
        "AFS_TOTAL",
        [
            {"coefficient": 31, "source_text": "31", "state": "SOURCE_NUMERIC"},
            {"coefficient": 9, "source_text": "9", "state": "SOURCE_NUMERIC"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    assert (
        _equation(
            equation_kind="TEST",
            components=components,
            result=result,
            canonical_unit="MILLION_VND",
        )["status"]
        == "MISMATCH"
    )


def test_terminal_unscoped_control_prefers_comprehensive_exact_frontier() -> None:
    result = _value_record(
        "UNSCOPED_TOTAL_CONTROL",
        [
            {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
            {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    afs = _value_record(
        "AFS_DEBT_GOVERNMENT",
        [
            {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
            {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    htm_zero = _value_record(
        "HTM_DEBT_CREDIT_INSTITUTIONS",
        [
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    equations = [
        _equation(equation_kind="NARROW", components=[afs], result=result),
        _equation(
            equation_kind="COMPREHENSIVE",
            components=[afs, htm_zero],
            result=result,
        ),
    ]
    selected, receipt = _select_unscoped_closing_equation(
        equations, terminal_control=True
    )
    assert selected is not None
    assert selected["equation_kind"] == "COMPREHENSIVE"
    assert receipt["disposition"] == (
        "TERMINAL_STRUCTURALLY_COMPREHENSIVE_EXACT_FRONTIER"
    )


def test_nonterminal_unscoped_control_keeps_narrow_exact_frontier() -> None:
    result = _value_record(
        "UNSCOPED_TOTAL_CONTROL",
        [
            {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
            {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    afs = _value_record(
        "AFS_DEBT_GOVERNMENT",
        [
            {"coefficient": 10, "source_text": "10", "state": "SOURCE_NUMERIC"},
            {"coefficient": 8, "source_text": "8", "state": "SOURCE_NUMERIC"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    htm_zero = _value_record(
        "HTM_DEBT_CREDIT_INSTITUTIONS",
        [
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
            {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        ],
        [],
        "SOURCE_OBSERVED_ROW",
    )
    equations = [
        _equation(equation_kind="NARROW", components=[afs], result=result),
        _equation(
            equation_kind="COMPREHENSIVE",
            components=[afs, htm_zero],
            result=result,
        ),
    ]
    selected, receipt = _select_unscoped_closing_equation(
        equations, terminal_control=False
    )
    assert selected is not None
    assert selected["equation_kind"] == "NARROW"
    assert receipt["disposition"] == "NONTERMINAL_NARROW_EXACT_FRONTIER"
