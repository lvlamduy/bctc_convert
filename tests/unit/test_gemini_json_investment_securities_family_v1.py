from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_investment_securities_family_v1 import (
    READY,
    UNRESOLVED,
    GeminiJsonInvestmentSecuritiesFamilyV1Error,
    build_gemini_json_investment_securities_region_query_receipt_v1,
    coalesce_gemini_json_investment_securities_document_v1,
    compile_gemini_json_investment_securities_family_specs_v1,
    evaluate_gemini_json_investment_securities_family_cluster_v1,
    validate_gemini_json_investment_securities_family_candidate_replay_v1,
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


def test_quality_blank_is_zero_only_after_visible_total_closes_both_lanes() -> None:
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
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert candidate["status"] == READY
    assert [cell["coefficient"] for cell in by_role["QUALITY_WATCH"]["values"]] == [0, 0]
    assert all(cell["state"].startswith("INFERRED_") for cell in by_role["QUALITY_WATCH"]["values"])


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
