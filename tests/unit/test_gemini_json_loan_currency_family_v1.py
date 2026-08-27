from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION_ID = "gfpstorev1:json:" + "a" * 64


def _specs() -> tuple[dict, dict, dict]:
    config_root = ROOT / "config/families"
    return tuple(
        json.loads((config_root / f"tm-loan-currency-classification-{name}-v1.json").read_text())
        for name in ("topology", "evaluation", "schema-binding")
    )


def _compiled() -> dict:
    return compile_gemini_json_flat_family_specs_v1(*_specs())


def _row(
    label: str | None,
    values: list[str | None],
    *,
    owner: str | None = None,
    row_kind: str = "ITEM",
) -> dict:
    return {
        "hierarchy_path_exact": [value for value in (owner, label) if value is not None] or [None],
        "label_exact": label,
        "row_kind": row_kind,
        "values_exact": values,
    }


def _page(shape: str) -> dict:
    if shape == "QUALIFIED_CORE":
        rows = [
            _row("Cho vay bằng Đồng Việt Nam", ["100", "90"]),
            _row("Cho vay bằng ngoại tệ", ["20", "10"]),
            _row("Tổng", ["120", "100"], row_kind="TOTAL"),
        ]
        table_title = "9.5 Theo loại tiền tệ"
    elif shape == "SCOPED_CORE_AND_DEFERRED_LC":
        core_owner = "Cho vay khách hàng"
        deferred_owner = (
            "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024"
        )
        rows = [
            _row(core_owner, ["120", "100"], row_kind="GROUP"),
            _row("Bằng VND", ["100", "90"], owner=core_owner),
            _row("Bằng ngoại tệ", ["20", "10"], owner=core_owner),
            _row(deferred_owner, ["5", "4"], row_kind="GROUP"),
            _row("Bằng VND", ["-", "1"], owner=deferred_owner),
            _row("Bằng ngoại tệ", ["5", "3"], owner=deferred_owner),
            _row(None, ["125", "104"], row_kind="TOTAL"),
        ]
        table_title = "Phân tích dư nợ cho vay theo loại tiền tệ"
    else:  # pragma: no cover - fixture guard
        raise AssertionError(shape)
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "CHO VAY KHÁCH HÀNG",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31.12.2025", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31.12.2024", "Triệu VND"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": table_title,
                        "unit_exact": "Triệu VND",
                    }
                ],
            }
        ],
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
    }


def _evaluate(page: dict) -> dict:
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id=VERSION_ID,
        physical_page=20,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled(),
    )


@pytest.mark.parametrize("shape", ["QUALIFIED_CORE", "SCOPED_CORE_AND_DEFERRED_LC"])
def test_currency_shapes_close_but_emit_only_two_schema_children(shape: str) -> None:
    result = _evaluate(_page(shape))

    assert result["status"] == READY
    assert result["reasons"] == []
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [757, 758]
    assert [mapping["role"] for mapping in result["mappings"]] == [
        "VND_LOANS",
        "FOREIGN_CURRENCY_AND_GOLD_LOANS",
    ]
    assert 756 not in [mapping["report_norm_id"] for mapping in result["mappings"]]
    assert result["closure_receipt"]["family_root_mapping_policy"] == (
        "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY"
    )
    assert result["closure_receipt"]["equations"][-1]["result_role"] == (
        "LOAN_CURRENCY_CLASSIFICATION"
    )


def test_repeated_currency_labels_are_role_scoped_and_deferred_rows_are_source_only() -> None:
    result = _evaluate(_page("SCOPED_CORE_AND_DEFERRED_LC"))

    assert result["status"] == READY
    assert [mapping["row_id"] for mapping in result["mappings"]] == ["r2", "r3"]
    deferred_receipt = next(
        equation
        for equation in result["closure_receipt"]["equations"]
        if equation["result_role"] == "DEFERRED_LC_PRE_2024_GROUP"
    )
    assert deferred_receipt["component_roles"] == ["DEFERRED_LC_VND", "DEFERRED_LC_FOREIGN"]
    assert deferred_receipt["component_row_ids"] == ["r5", "r6"]
    assert all(mapping["row_id"] not in {"r5", "r6"} for mapping in result["mappings"])

    unscoped = _page("QUALIFIED_CORE")
    unscoped_rows = unscoped["sections"][0]["tables"][0]["rows"]
    unscoped_rows[0]["label_exact"] = "Bằng VND"
    unscoped_rows[0]["hierarchy_path_exact"] = ["Bằng VND"]
    unscoped_rows[1]["label_exact"] = "Bằng ngoại tệ"
    unscoped_rows[1]["hierarchy_path_exact"] = ["Bằng ngoại tệ"]
    unresolved = _evaluate(unscoped)
    assert unresolved["status"] == UNRESOLVED
    assert unresolved["mappings"] == []


def test_hard_negative_currency_risk_title_vetoes_same_numeric_pair() -> None:
    page = _page("QUALIFIED_CORE")
    page["sections"][0]["tables"][0]["title_exact"] = "Phân tích rủi ro tiền tệ"

    result = _evaluate(page)

    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert "HARD_NEGATIVE_FAMILY_TITLE_PRESENT" in result["reasons"]


def test_context_only_family_root_is_never_mapped_but_must_close_exactly() -> None:
    good = _evaluate(_page("QUALIFIED_CORE"))
    assert good["status"] == READY
    assert all(mapping["report_norm_id"] != 756 for mapping in good["mappings"])

    page = deepcopy(_page("QUALIFIED_CORE"))
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "121"
    bad = _evaluate(page)
    assert bad["status"] == UNRESOLVED
    assert bad["mappings"] == []
    assert "FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED" in bad["reasons"]


def test_currency_family_accepts_only_two_money_lanes() -> None:
    compiled = _compiled()

    assert compiled["evaluation"]["expected_lane_unit_kind_alternatives"] == [["MONEY", "MONEY"]]
    assert compiled["evaluation"]["hierarchical_closure_spec"][
        "rounding_lane_unit_kind_alternatives"
    ] == [["MONEY", "MONEY"]]


def test_database_query_separates_qualified_rows_from_owner_scoped_short_rows() -> None:
    compiled = _compiled()
    query_groups = compiled["query_anchor_alias_groups"]

    assert len(compiled["anchor_alias_groups"]) == 1
    assert len(query_groups) == 2
    qualified = next(group for group in query_groups if len(group) == 2)
    owner_scoped = next(group for group in query_groups if len(group) == 3)
    assert "Cho vay bằng VND" in qualified[0]
    assert "Bằng VND" not in qualified[0]
    assert "Cho vay bằng ngoại tệ" in qualified[1]
    assert "Bằng ngoại tệ" not in qualified[1]
    assert "Cho vay khách hàng" in owner_scoped[0]
    assert owner_scoped[1] == ["Bằng VND", "Bằng đồng Việt Nam"]
    assert "Bằng ngoại tệ" in owner_scoped[2]


def test_scoped_only_query_stays_owner_bound_and_ignores_nonanchor_owner_aliases() -> None:
    topology, evaluation, schema = deepcopy(_specs())
    children = {child["role"]: child for child in topology["children"]}
    for role in ("VND_LOANS", "FOREIGN_CURRENCY_AND_GOLD_LOANS"):
        children[role]["matchers"] = [
            matcher
            for matcher in children[role]["matchers"]
            if matcher["within_role"] == "CORE_TOTAL_GROUP"
        ]
    children["CORE_TOTAL_GROUP"]["matchers"].append(
        {
            "aliases": ["Không dùng làm query owner"],
            "presence_anchor": False,
            "within_role": None,
        }
    )

    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)

    assert len(compiled["query_anchor_alias_groups"]) == 1
    owner_scoped = compiled["query_anchor_alias_groups"][0]
    assert len(owner_scoped) == 3
    assert "Cho vay khách hàng" in owner_scoped[0]
    assert "Không dùng làm query owner" not in owner_scoped[0]
    assert owner_scoped[1] == ["Bằng VND", "Bằng đồng Việt Nam"]
