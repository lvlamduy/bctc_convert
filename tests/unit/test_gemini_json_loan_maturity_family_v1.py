from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)
from bctc_ai.evaluation.gemini_json_region_repair_queue_v1 import (
    build_family_region_repair_plans_v1,
)

ROOT = Path(__file__).resolve().parents[2]
VERSION_ID = "gfpstorev1:json:" + "9" * 64


def _specs() -> tuple[dict, dict, dict]:
    config_root = ROOT / "config/families"
    return tuple(
        json.loads((config_root / f"tm-loan-maturity-buckets-{name}-v1.json").read_text())
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


def _page(
    shape: str,
    *,
    headers: tuple[str, str] = ("31.12.2025", "31.12.2024"),
) -> dict:
    core_owner = "Dư nợ cho vay"
    core_rows = [
        _row("Nợ ngắn hạn", ["100", "90"]),
        _row("Nợ trung hạn", ["20", "10"]),
        _row("Nợ dài hạn", ["30", "20"]),
    ]
    if shape == "CORE_ONLY":
        rows = [*core_rows, _row(None, ["150", "120"], row_kind="TOTAL")]
    elif shape == "CORE_MARGIN_NO_SUBTOTAL":
        rows = [
            *core_rows,
            _row(
                "Cho vay giao dịch ký quỹ và ứng trước cho khách hàng",
                ["7", "6"],
            ),
            _row(None, ["157", "126"], row_kind="TOTAL"),
        ]
    elif shape == "PRINTED_CORE_MARGIN":
        rows = [
            _row(core_owner, ["150", "120"], row_kind="GROUP"),
            *[_row(row["label_exact"], row["values_exact"], owner=core_owner) for row in core_rows],
            _row(
                "Các khoản cho vay margin chứng khoán và ứng trước khách hàng tại MBS",
                ["7", "6"],
            ),
            _row(None, ["157", "126"], row_kind="TOTAL"),
        ]
    elif shape == "DIRECT_DELAYED_LC":
        rows = [
            *core_rows,
            _row(None, ["150", "120"], row_kind="SUBTOTAL"),
            _row(
                "Nợ ngắn hạn - Nghiệp vụ phát hành thư tín dụng trả chậm có điều khoản "
                "thanh toán trả ngay hoặc trả trước phát sinh trước 01/07/2024",
                ["5", "4"],
            ),
            _row(None, ["155", "124"], row_kind="TOTAL"),
        ]
    elif shape == "GROUPED_DELAYED_LC":
        delayed_owner = (
            "Nghiệp vụ phát hành thư tín dụng trả chậm phát sinh trước ngày 01 tháng 7 năm 2024"
        )
        rows = [
            _row(core_owner, ["150", "120"], row_kind="GROUP"),
            *[_row(row["label_exact"], row["values_exact"], owner=core_owner) for row in core_rows],
            _row(delayed_owner, ["5", "4"], row_kind="GROUP"),
            _row("Nợ ngắn hạn", ["5", "4"], owner=delayed_owner),
            _row(None, ["155", "124"], row_kind="TOTAL"),
        ]
    else:  # pragma: no cover - test fixture guard
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
                                "header_path_exact": [headers[0], "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": [headers[1], "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": "Phân tích dư nợ theo thời gian cho vay",
                        "unit_exact": "Triệu đồng",
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


@pytest.mark.parametrize(
    ("shape", "expected_report_norm_ids"),
    [
        ("CORE_ONLY", [753, 754, 755]),
        ("CORE_MARGIN_NO_SUBTOTAL", [753, 754, 755, 5747]),
        ("PRINTED_CORE_MARGIN", [753, 754, 755, 5747]),
        ("DIRECT_DELAYED_LC", [753, 754, 755]),
        ("GROUPED_DELAYED_LC", [753, 754, 755]),
    ],
)
def test_five_maturity_shapes_close_but_emit_only_bound_children(
    shape: str, expected_report_norm_ids: list[int]
) -> None:
    result = _evaluate(_page(shape))

    assert result["status"] == READY
    assert result["reasons"] == []
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == (
        expected_report_norm_ids
    )
    assert 752 not in expected_report_norm_ids
    assert 1944 not in expected_report_norm_ids
    assert result["closure_receipt"]["family_root_mapping_policy"] == (
        "REQUIRE_HIERARCHICALLY_RESOLVED_CONTEXT_ONLY"
    )
    assert result["closure_receipt"]["equations"][-1]["result_role"] == ("LOAN_MATURITY_BUCKETS")


def test_context_only_root_still_requires_one_exact_root_closure() -> None:
    page = _page("CORE_ONLY")
    page["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "151"

    result = _evaluate(page)

    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert "FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED" in result["reasons"]


def test_compiler_keeps_raw_punctuation_for_database_query_only() -> None:
    compiled = _compiled()
    raw_aliases = {
        alias
        for group in compiled["query_anchor_alias_groups"]
        for aliases in group
        for alias in aliases
    }

    assert "Nợ ngắn hạn (đến 01 năm)" in raw_aliases
    assert "Nợ ngắn hạn (đến 01 năm)" not in compiled["aliases_by_role"]["SHORT_TERM"]
    assert "no ngan han den 01 nam" in compiled["aliases_by_role"]["SHORT_TERM"]
    assert "Phân tích dư nợ theo thời gian" in compiled["query_parent_aliases"]
    assert "Nợ ngắn hạn (đến 01 năm)" in compiled["query_aliases_by_role"]["SHORT_TERM"]
    assert "Cho vay khách hàng" not in compiled["query_aliases_by_role"]["SHORT_TERM"]


def test_unambiguous_mdy_fallback_does_not_change_ambiguous_dmy_authority() -> None:
    mdy = _evaluate(_page("CORE_ONLY", headers=("12/31/2025", "12/31/2024")))
    ambiguous = _evaluate(_page("CORE_ONLY", headers=("11/12/2025", "10/12/2024")))

    assert mdy["status"] == READY
    assert mdy["closure_receipt"]["period_value_column_axis"]["period_signatures"] == [
        ["DATE", "2025-12-31"],
        ["DATE", "2024-12-31"],
    ]
    assert ambiguous["status"] == READY
    assert ambiguous["closure_receipt"]["period_value_column_axis"]["period_signatures"] == [
        ["DATE", "2025-12-11"],
        ["DATE", "2024-12-10"],
    ]


def test_hierarchical_period_failure_builds_bounded_table_axis_repair() -> None:
    topology, evaluation, schema = _specs()
    compiled = _compiled()
    page = _page("CORE_ONLY")
    page["sections"][0]["tables"][0]["columns"][0]["header_path_exact"] = [
        "Không rõ kỳ hiện tại",
        "Triệu đồng",
    ]
    candidate = _evaluate(page)
    assert "CURRENT_AND_COMPARATIVE_PERIOD_HEADERS_ARE_NOT_EXACT" in candidate["reasons"]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "8" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[
            {
                "candidate_count": 1,
                "candidates": [candidate],
                "document_ordinal": 1,
                "mappings": [],
                "reasons": candidate["reasons"],
                "selected_candidate_id": None,
                "source_logical_name": "generic/maturity.pdf",
                "source_sha256": "7" * 64,
                "status": UNRESOLVED,
            }
        ],
    )

    plans = build_family_region_repair_plans_v1(
        sweep=sweep,
        page_json_by_version={VERSION_ID: deepcopy(page)},
        compiled_specs=compiled,
    )

    assert len(plans) == 1
    assert plans[0]["repair_scope"] == "TABLE_PERIOD_AXIS"
    assert plans[0]["trigger_kinds"] == ["TABLE_PERIOD_AXIS_INCOMPLETE"]
    assert plans[0]["target_table_refs"] == [{"section_id": "s1", "table_id": "t1"}]
