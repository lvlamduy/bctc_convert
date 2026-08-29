from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
    evaluate_gemini_json_multitable_hierarchical_family_cluster_v1,
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_ID = "gfpstorev1:json:" + "b" * 64
SOURCE_SHA256 = "c" * 64
ROOT_LABEL = "Thu nhập từ góp vốn, mua cổ phần"
DIRECT = "Cổ tức nhận được trong kỳ từ góp vốn, mua cổ phần"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        _json("tm-capital-contribution-dividend-income-topology-v1.json"),
        _json("tm-capital-contribution-dividend-income-evaluation-v1.json"),
        _json("tm-capital-contribution-dividend-income-schema-binding-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
    path: list[str | None] | None = None,
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": (
            [value for value in path if value is not None]
            if path is not None
            else [value for value in (ROOT_LABEL, label) if value is not None]
        ),
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _table(rows: list[dict[str, Any]], *, title: str | None = None) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Năm 2026", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Năm 2025", "Triệu đồng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": "Triệu đồng",
    }


def _ordinary_page() -> dict[str, Any]:
    rows = [
        _row(DIRECT, ["80", "60"], kind="SUBTOTAL", path=[ROOT_LABEL, DIRECT]),
        _row(
            "Từ chứng khoán vốn kinh doanh",
            ["30", "20"],
            path=[ROOT_LABEL, DIRECT, "Từ chứng khoán vốn kinh doanh"],
        ),
        _row(
            "Từ chứng khoán vốn đầu tư",
            ["20", "15"],
            path=[ROOT_LABEL, DIRECT, "Từ chứng khoán vốn đầu tư"],
        ),
        _row(
            "Từ góp vốn, đầu tư dài hạn",
            ["30", "25"],
            path=[ROOT_LABEL, DIRECT, "Từ góp vốn, đầu tư dài hạn"],
        ),
        _row(
            "Phân chia lãi theo phương pháp vốn chủ sở hữu của các khoản đầu tư vào công ty liên doanh",
            ["10", "5"],
        ),
        _row("Các khoản thu nhập khác", ["5", "2"]),
        _row(None, ["95", "67"], kind="TOTAL", path=[ROOT_LABEL]),
    ]
    return _page([_table(rows)])


def _ctg_page(*, total: tuple[str, str] = ("247", "211")) -> dict[str, Any]:
    return _page(
        [
            _table(
                [
                    _row("- Từ chứng khoán Vốn", ["-", "-"], path=["- Từ chứng khoán Vốn"]),
                    _row(
                        "- Từ góp vốn, đầu tư dài hạn",
                        ["247", "211"],
                        path=["- Từ góp vốn, đầu tư dài hạn"],
                    ),
                    _row(None, list(total), kind="TOTAL", path=[None]),
                ],
                title=DIRECT,
            )
        ]
    )


def _page(tables: list[dict[str, Any]], *, title: str = ROOT_LABEL) -> dict[str, Any]:
    return {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": title,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _record(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "page_json": page,
        "page_json_version_id": VERSION_ID,
        "physical_page": 1,
        "selected_page_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }


def _cluster(page: dict[str, Any]) -> dict[str, Any]:
    return coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=[_record(page)], compiled_specs=_compiled()
    )


def _evaluate(
    page: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    cluster = _cluster(page)
    assert cluster["status"] == READY
    regions = cluster["component_regions"]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(regions)
    candidate = evaluate_gemini_json_multitable_hierarchical_family_cluster_v1(
        regions=regions,
        page_json_by_version={VERSION_ID: page},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )
    return candidate, regions, receipt


def test_complete_visible_hierarchy_maps_root_and_declared_children() -> None:
    candidate, regions, receipt = _evaluate(_ordinary_page())
    assert candidate["status"] == READY
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]} == set(
        range(1198, 1205)
    )
    validate_gemini_json_multitable_hierarchical_family_candidate_replay_v1(
        candidate,
        regions=regions,
        page_json_by_version={VERSION_ID: _ordinary_page()},
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )


def test_source_only_combined_equity_row_is_not_split_and_closes_root() -> None:
    candidate, _regions, _receipt = _evaluate(_ctg_page())
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "DIRECT_DIVIDEND",
        "FAMILY_ROOT_TOTAL",
        "LONG_TERM_CAPITAL_DIVIDEND",
    }
    assert {mapping["report_norm_id"] for mapping in candidate["mappings"]}.isdisjoint({1200, 1201})
    source_only = candidate["closure_receipt"]["source_only_unmapped_rows"]
    assert len(source_only) == 1
    assert source_only[0]["consumed_by_exact_equation"] is True


def test_source_only_frontier_mismatch_is_unresolved_without_mappings() -> None:
    candidate, _regions, _receipt = _evaluate(_ctg_page(total=("248", "211")))
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_multiline_parent_and_child_surface_resolves_to_the_declared_leaf() -> None:
    combined_label = (
        "Cổ tức nhận được; lãi được chia trong kỳ từ góp vốn, mua cổ phần:\n"
        "- Từ góp vốn, đầu tư dài hạn"
    )
    page = _page(
        [
            _table(
                [
                    _row(combined_label, ["220.392", "205.774"], path=[combined_label]),
                    _row(None, ["220.392", "205.774"], path=[combined_label, None]),
                    _row(None, ["220.392", "205.774"], kind="TOTAL", path=[None]),
                ],
                title=ROOT_LABEL,
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "DIRECT_DIVIDEND",
        "FAMILY_ROOT_TOTAL",
        "LONG_TERM_CAPITAL_DIVIDEND",
    }


def test_declared_acronym_and_bounded_note_reference_variants_close_locally() -> None:
    page = _page(
        [
            _table(
                [
                    _row(
                        "Cổ tức nhận được từ các khoản góp vốn, mua cổ phần (Thuyết minh 33(a))",
                        ["10", "8"],
                    ),
                    _row(
                        "Phân chia lãi/lỗ theo phương pháp VCSH của các khoản đầu tư "
                        "vào các công ty liên doanh, liên kết",
                        ["3", "2"],
                    ),
                    _row(None, ["13", "10"], kind="TOTAL", path=[None]),
                ]
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} == {
        "DIRECT_DIVIDEND",
        "EQUITY_METHOD",
        "FAMILY_ROOT_TOTAL",
    }


def test_missing_direct_subtotal_is_derived_without_absorbing_equity_method() -> None:
    investment = "Cổ tức nhận được từ chứng khoán vốn đầu tư"
    long_term = "Cổ tức nhận được từ góp vốn, đầu tư dài hạn"
    equity = (
        "Phân chia lãi/lỗ theo phương pháp VCSH của các khoản đầu tư "
        "vào các công ty liên doanh, liên kết"
    )
    page = _page(
        [
            _table(
                [
                    _row(investment, ["5", "4"], path=[ROOT_LABEL, DIRECT, investment]),
                    _row(long_term, ["7", "6"], path=[ROOT_LABEL, DIRECT, long_term]),
                    _row(equity, ["3", "2"], path=[ROOT_LABEL, equity]),
                    _row(None, ["15", "12"], kind="TOTAL", path=[ROOT_LABEL]),
                ],
                title=DIRECT,
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    by_role = {mapping["role"]: mapping for mapping in candidate["mappings"]}
    assert [cell["coefficient"] for cell in by_role["DIRECT_DIVIDEND"]["values"]] == [12, 10]
    assert [cell["coefficient"] for cell in by_role["EQUITY_METHOD"]["values"]] == [3, 2]
    assert [cell["coefficient"] for cell in by_role["FAMILY_ROOT_TOTAL"]["values"]] == [15, 12]
    assert by_role["DIRECT_DIVIDEND"]["state"] == (
        "STRUCTURAL_PARENT_DERIVED_FROM_COMPLETE_VISIBLE_SCOPED_CHILD_FRONTIER"
    )
    assert by_role["FAMILY_ROOT_TOTAL"]["state"] == (
        "SOURCE_VISIBLE_FAMILY_ROOT_TOTAL_PROVEN_AFTER_DERIVED_STRUCTURAL_PARENT_CLOSURE"
    )


def test_one_exact_family_root_row_maps_without_tautological_equation() -> None:
    page = _page(
        [
            _table(
                [_row(ROOT_LABEL, ["-", "-"], kind="TOTAL", path=[ROOT_LABEL])],
                title=ROOT_LABEL,
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == READY
    assert [(mapping["role"], mapping["report_norm_id"]) for mapping in candidate["mappings"]] == [
        ("FAMILY_ROOT_TOTAL", 1198)
    ]
    receipt = candidate["closure_receipt"]["root_component_sum_receipts"]
    assert len(receipt) == 1
    assert receipt[0]["coefficients"] == [0, 0]
    assert receipt[0]["component_roles"] == []
    assert receipt[0]["result_role"] == "FAMILY_ROOT_TOTAL"
    assert receipt[0]["rule"] == "SOLE_SOURCE_VISIBLE_FAMILY_ROOT_ROW_NO_SELF_EQUATION"
    assert len(receipt[0]["source_refs"]) == 1


def test_root_row_fallback_does_not_ignore_an_adjacent_money_row() -> None:
    page = _page(
        [
            _table(
                [
                    _row(ROOT_LABEL, ["10", "8"], kind="TOTAL"),
                    _row("Khoản mục ngoài graph family", ["1", "1"]),
                ],
                title=ROOT_LABEL,
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_exact_total_does_not_consume_an_undeclared_top_level_source_row() -> None:
    page = _page(
        [
            _table(
                [
                    _row(DIRECT, ["10", "8"], path=[DIRECT]),
                    _row("Khoản mục nguồn chưa khai báo", ["1", "1"], path=["Khoản mục nguồn"]),
                    _row(None, ["11", "9"], kind="TOTAL", path=[None]),
                ]
            )
        ]
    )
    candidate, _regions, _receipt = _evaluate(page)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "UNMAPPED_TOP_LEVEL_SOURCE_ONLY_ROW_NOT_DECLARED_VALIDATION_ROLE"
    ]


def test_unknown_component_and_duplicate_population_fail_closed() -> None:
    unknown = _ctg_page()
    unknown["sections"][0]["tables"][0]["rows"][1]["values_exact"][0] = None
    candidate, _regions, _receipt = _evaluate(unknown)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []

    duplicate = _ordinary_page()
    duplicate["sections"][0]["tables"].append(copy.deepcopy(duplicate["sections"][0]["tables"][0]))
    candidate, _regions, _receipt = _evaluate(duplicate)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_period_and_unit_conflicts_fail_closed() -> None:
    period = _ordinary_page()
    period["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Năm 2026",
        "Năm trước",
        "Triệu đồng",
    ]
    candidate, _regions, _receipt = _evaluate(period)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []

    unit = _ordinary_page()
    unit["sections"][0]["tables"][0]["unit_exact"] = "Triệu đồng; Nghìn đồng"
    candidate, _regions, _receipt = _evaluate(unit)
    assert candidate["status"] == UNRESOLVED
    assert candidate["mappings"] == []


def test_cash_flow_lookalike_is_not_observed() -> None:
    page = _page(
        [_table([_row("Thu cổ tức", ["10", "8"], kind="TOTAL")], title="Thu cổ tức")],
        title="Tiền thu cổ tức và lợi nhuận được chia từ các khoản đầu tư, góp vốn dài hạn",
    )
    page["sections"][0]["content_kind"] = "PRIMARY_STATEMENT"
    page["sections"][0]["statement_type"] = "CASH_FLOW"
    cluster = _cluster(page)
    assert cluster["status"] == NOT_OBSERVED
    assert cluster["component_regions"] == []
