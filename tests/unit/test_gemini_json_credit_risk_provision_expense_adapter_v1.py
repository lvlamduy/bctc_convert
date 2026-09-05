from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
    _apply_document_repairs,
    _family37_period_compatibility_v1,
    _family37_period_scope_v1,
    build_credit_risk_provision_expense_source_row_coverage_receipt_v1,
    build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1,
    build_gemini_json_credit_risk_provision_expense_trials_v1,
    compile_gemini_json_credit_risk_provision_expense_family_specs_v1,
    evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1,
    validate_gemini_json_credit_risk_provision_expense_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
    build_gemini_json_multitable_hierarchical_region_query_receipt_v1,
    coalesce_gemini_json_multitable_hierarchical_document_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ID = "gfpstorev1:document:" + "a" * 64
VERSION_1 = "gfpstorev1:json:" + "b" * 64
VERSION_2 = "gfpstorev1:json:" + "d" * 64
SOURCE_SHA256 = "c" * 64
OWNER = "Chi phí dự phòng rủi ro tín dụng"


def _json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "config/families" / name).read_bytes())


def _compiled() -> dict[str, Any]:
    return compile_gemini_json_credit_risk_provision_expense_family_specs_v1(
        _json("tm-credit-risk-provision-expense-topology-v1.json"),
        _json("tm-credit-risk-provision-expense-evaluation-v1.json"),
        _json("tm-credit-risk-provision-expense-schema-binding-v1.json"),
        _json("tm-credit-risk-provision-expense-source-repair-v1.json"),
    )


def _row(
    label: str | None,
    values: list[str | None],
    *,
    kind: str = "ITEM",
) -> dict[str, Any]:
    return {
        "hierarchy_path_exact": [] if label is None else [label],
        "label_exact": label,
        "row_kind": kind,
        "values_exact": values,
    }


def _normal_page(
    rows: list[dict[str, Any]],
    *,
    columns: list[dict[str, Any]] | None = None,
    unit: str | None = "Triệu đồng",
) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    {
                        "columns": columns
                        or [
                            {
                                "header_path_exact": ["Năm nay"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm trước"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": unit,
                    }
                ],
                "title_exact": OWNER,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def _primary_page(current: str, comparative: str) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "INCOME_STATEMENT",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Năm nay", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Năm trước", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [_row(OWNER, [current, comparative])],
                        "title_exact": "Báo cáo kết quả hoạt động",
                        "unit_exact": "Triệu đồng",
                    }
                ],
                "title_exact": "Báo cáo kết quả hoạt động",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _primary_page_with_exact_ranges(
    current: str,
    comparative: str,
    *,
    current_start: str = "01/01/2025",
    current_end: str = "31/03/2025",
    comparative_start: str = "01/01/2024",
    comparative_end: str = "31/03/2024",
) -> dict[str, Any]:
    page = _primary_page(current, comparative)
    columns = page["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"] = [
        f"Kỳ này từ {current_start} đến {current_end}",
        "Triệu đồng",
    ]
    columns[1]["header_path_exact"] = [
        f"Kỳ trước từ {comparative_start} đến {comparative_end}",
        "Triệu đồng",
    ]
    return page


def _customer_balance_page(
    current: str, comparative: str, *, unit: str = "Triệu đồng"
) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "PRIMARY_STATEMENT",
                "narratives_exact": [],
                "statement_type": "BALANCE_SHEET",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["Số dư cuối quý"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["Số dư đầu năm"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            _row(
                                "Dự phòng rủi ro cho vay khách hàng",
                                [current, comparative],
                            )
                        ],
                        "title_exact": "Báo cáo tình hình tài chính",
                        "unit_exact": unit,
                    }
                ],
                "title_exact": "Báo cáo tình hình tài chính",
            }
        ],
        "status": "PRIMARY_FINANCIAL_STATEMENT",
    }


def _run_pages(
    pages: list[tuple[str, int, dict[str, Any]]],
    *,
    reverse_page_map: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[int, dict[str, dict[str, Any]]]]:
    compiled = _compiled()
    records = []
    selected_pages = []
    by_version = {}
    for selected_ordinal, (version_id, physical_page, page) in enumerate(pages, 1):
        record = {
            "document_id": DOCUMENT_ID,
            "document_ordinal": 1,
            "page_json": page,
            "page_json_version_id": version_id,
            "physical_page": physical_page,
            "selected_page_ordinal": selected_ordinal,
            "source_logical_name": "fixture.pdf",
            "source_sha256": SOURCE_SHA256,
        }
        records.append(record)
        selected_pages.append({key: value for key, value in record.items() if key != "page_json"})
        by_version[version_id] = page
    document = {
        "document_id": DOCUMENT_ID,
        "document_ordinal": 1,
        "source_logical_name": "fixture.pdf",
        "source_sha256": SOURCE_SHA256,
    }
    cluster = coalesce_gemini_json_multitable_hierarchical_document_v1(
        page_records=records, compiled_specs=compiled
    )
    base = build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=[document],
        selected_page_axis=selected_pages,
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(compiled["query_policy"]),
    )
    page_json_by_document = {
        1: (
            dict(reversed(list(by_version.items())))
            if reverse_page_map
            else by_version
        )
    }
    indexed = build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1(
        base_indexed_query_evidence=base,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    trials = build_gemini_json_credit_risk_provision_expense_trials_v1(
        indexed_query_evidence=indexed,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    validate_gemini_json_credit_risk_provision_expense_replay_v1(
        base_indexed_query_evidence=base,
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=page_json_by_document,
        compiled_specs=compiled,
    )
    return indexed, trials, page_json_by_document


def _mapped(trial: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {mapping["role"]: mapping for mapping in trial["mappings"]}


def test_direct_terminal_total_prevents_parent_child_double_count() -> None:
    rows = [
        _row("Trích lập dự phòng cụ thể cấp tín dụng cho các TCTD khác", ["-", "5"]),
        _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
        _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
        _row(None, ["100", "85"], kind="TOTAL"),
    ]
    _indexed, trials, _pages = _run_pages([(VERSION_1, 1, _normal_page(rows))])
    trial = trials[0]
    assert trial["status"] == READY
    mapped = _mapped(trial)
    assert [cell["coefficient"] for cell in mapped["FAMILY_ROOT_TOTAL"]["values"]] == [
        100,
        85,
    ]
    assert mapped["FAMILY_ROOT_TOTAL"]["values"][1]["source_text"] == "85"


def test_two_other_rows_are_summed_without_losing_original_source_labels() -> None:
    rows = [
        _row("Trích lập dự phòng chung cho vay khách hàng", ["10", "9"]),
        _row("Hoàn nhập dự phòng cho khoản phải thu từ hợp đồng bán nợ", ["(2)", "(1)"]),
        _row("Hoàn nhập dự phòng cho các tài sản có rủi ro tín dụng khác", ["(3)", "(4)"]),
        _row(None, ["5", "4"], kind="TOTAL"),
    ]
    _indexed, trials, _pages = _run_pages([(VERSION_1, 1, _normal_page(rows))])
    candidate = trials[0]["candidates"][0]
    mapping = _mapped(trials[0])["OTHER_PROVISION"]
    assert [cell["coefficient"] for cell in mapping["values"]] == [-5, -5]
    assert {ref["label_exact"] for ref in mapping["source_refs"]} == {
        "Hoàn nhập dự phòng cho khoản phải thu từ hợp đồng bán nợ",
        "Hoàn nhập dự phòng cho các tài sản có rủi ro tín dụng khác",
    }
    for final_mapping in candidate["mappings"]:
        material = {
            key: value
            for key, value in final_mapping.items()
            if key != "item_mapping_id"
        }
        assert final_mapping["item_mapping_id"] == (
            "gjmthfmv1:item:" + canonical_json_sha256_v1(material)
        )
    for equation in candidate["closure_receipt"]["equations"]:
        material = {
            key: value for key, value in equation.items() if key != "equation_id"
        }
        prefix = equation["equation_id"].rsplit(":", 1)[0]
        assert equation["equation_id"] == (
            prefix + ":" + canonical_json_sha256_v1(material)
        )


def test_narrow_customer_row_is_widened_only_by_visible_component_sum() -> None:
    rows = [
        _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
        _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
        _row("Trích lập dự phòng cho vay giao dịch ký quỹ và ứng trước", ["3", "2"]),
        _row(None, ["103", "82"], kind="TOTAL"),
    ]
    _indexed, trials, _pages = _run_pages([(VERSION_1, 1, _normal_page(rows))])
    customer = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in customer["values"]] == [103, 82]
    assert all(cell["source_text"] is None for cell in customer["values"])
    assert len(customer["source_refs"]) == 3


def test_partial_blank_role_lane_stays_null_while_root_remains_visible() -> None:
    rows = [
        _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
        _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
        _row("Trích lập dự phòng chung cho chứng khoán", ["3", None]),
        _row(None, ["103", "80"], kind="TOTAL"),
    ]
    _indexed, trials, _pages = _run_pages([(VERSION_1, 1, _normal_page(rows))])
    mapped = _mapped(trials[0])
    assert [cell["coefficient"] for cell in mapped["OTHER_PROVISION"]["values"]] == [
        3,
        None,
    ]
    assert mapped["OTHER_PROVISION"]["values"][1]["state"] == "BLANK_SOURCE_CELL"
    assert [cell["coefficient"] for cell in mapped["FAMILY_ROOT_TOTAL"]["values"]] == [
        103,
        80,
    ]


def test_equal_primary_values_cannot_supply_a_missing_note_unit() -> None:
    columns = [
        {
            "header_path_exact": ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm nay"],
            "value_kind": "MONEY",
        },
        {
            "header_path_exact": ["Luỹ kế từ đầu năm đến cuối kỳ này", "Năm trước"],
            "value_kind": "MONEY",
        },
    ]
    note = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ],
        columns=columns,
        unit=None,
    )
    original = canonical_clone_v1(note)
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _primary_page("(100)", "(80)")), (VERSION_2, 2, note)]
    )
    assert same_typed_json_v1(note, original)
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


@pytest.mark.parametrize(
    ("million_current", "million_prior", "vnd_current", "vnd_prior"),
    [
        ("100", "80", "100000000", "80000000"),
        ("100000000", "80000000", "100", "80"),
        ("100", "80", "100", "80"),
        ("(100)", "(80)", "(100000000)", "(80000000)"),
        ("999", "888", "100", "80"),
    ],
)
def test_conflicting_document_units_cannot_bind_unitless_note_by_value(
    million_current: str,
    million_prior: str,
    vnd_current: str,
    vnd_prior: str,
) -> None:
    primary_million = _primary_page(million_current, million_prior)
    primary_vnd = _primary_page(vnd_current, vnd_prior)
    primary_vnd["sections"][0]["tables"][0]["unit_exact"] = "VND"
    for column in primary_vnd["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0], "VND"]
    unitless_note = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ],
        unit=None,
    )

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary_million),
            (VERSION_2, 2, primary_vnd),
            ("gfpstorev1:json:" + "e" * 64, 3, unitless_note),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_position_only_movement_cannot_use_amount_to_choose_current_lane() -> None:
    def movement(title: str, values: list[str]) -> dict[str, Any]:
        return {
            "columns": [
                {"header_path_exact": ["Dự phòng chung"], "value_kind": "MONEY"},
                {"header_path_exact": ["Dự phòng cụ thể"], "value_kind": "MONEY"},
                {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
            ],
            "continuation": "NONE",
            "rows": [
                _row("Số dư đầu kỳ", ["1", "2", "3"]),
                _row("Dự phòng rủi ro trích lập trong kỳ", values),
                _row("Số dư cuối kỳ", ["11", "22", "33"], kind="TOTAL"),
            ],
            "title_exact": title,
            "unit_exact": None,
        }

    note = {
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    movement(
                        "Sự thay đổi của Dự phòng rủi ro tín dụng đối với dư nợ cho vay khách hàng\nSố cuối quý",
                        ["20", "80", "100"],
                    ),
                    movement("Số đầu năm", ["15", "65", "80"]),
                ],
                "title_exact": None,
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _primary_page("(103)", "(82)")), (VERSION_2, 2, note)]
    )
    trial = trials[0]
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []
    assert trial["candidate_count"] == 0


def _movement_table(
    rows: list[dict[str, Any]],
    *,
    title: str | None = None,
    unit: str | None = "Triệu đồng",
) -> dict[str, Any]:
    return {
        "columns": [
            {"header_path_exact": ["Dự phòng chung"], "value_kind": "MONEY"},
            {"header_path_exact": ["Dự phòng cụ thể"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": rows,
        "title_exact": title,
        "unit_exact": unit,
    }


def _movement_note(
    tables: list[dict[str, Any]], *, narratives: list[str] | None = None
) -> dict[str, Any]:
    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": narratives or [],
                "statement_type": "NOT_APPLICABLE",
                "tables": tables,
                "title_exact": "Dự phòng rủi ro cho vay khách hàng",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def test_relative_comparative_lane_without_exact_duration_is_unresolved() -> None:
    table = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Kỳ trước",
    )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([table]))]
    )
    trial = trials[0]
    assert trial["status"] == UNRESOLVED
    assert trial["mappings"] == []


def test_exact_comparative_movement_preserves_comparative_lane() -> None:
    table = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Kỳ trước từ 01/01/2025 đến 30/06/2025",
    )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([table]))]
    )
    trial = trials[0]
    assert trial["status"] == READY
    mapped = _mapped(trial)
    for role, comparative in (
        ("CUSTOMER_PROVISION", 100),
        ("CUSTOMER_GENERAL", 20),
        ("CUSTOMER_SPECIFIC", 80),
    ):
        assert [cell["coefficient"] for cell in mapped[role]["values"]] == [
            None,
            comparative,
        ]
        assert mapped[role]["values"][0]["state"] == "UNOBSERVED_SOURCE_LANE"


def test_single_opening_position_movement_fails_closed_as_ambiguous() -> None:
    table = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Số đầu năm",
    )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([table]))]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert trials[0]["reasons"] == ["F37_TRANSPOSED_PRESENTATION_NOT_UNIQUE"]


def test_single_unanchored_year_movement_fails_closed_as_ambiguous() -> None:
    action = _row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])
    action["hierarchy_path_exact"] = ["Năm 2024", action["label_exact"]]
    table = _movement_table([action])
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([table]))]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_local_unit_gross_net_ambiguity_without_primary_root_is_unresolved() -> None:
    tables = []
    for year, provision, reversal in (
        (2025, ["20", "80", "100"], ["(2)", "(8)", "(10)"]),
        (2024, ["15", "65", "80"], ["(1)", "(4)", "(5)"]),
    ):
        tables.append(
            _movement_table(
                [
                    _row("Trích lập dự phòng trong kỳ", provision),
                    _row("Hoàn nhập dự phòng trong kỳ", reversal),
                ],
                title=f"Sáu tháng kết thúc năm {year}",
            )
        )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note(tables))]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_multiple_compatible_primary_roots_are_unresolved_not_unobserved() -> None:
    table = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Kỳ này",
    )
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(100)", "(80)")),
            (VERSION_2, 2, _primary_page("(110)", "(90)")),
            (
                "gfpstorev1:json:" + "e" * 64,
                3,
                _movement_note([table]),
            ),
        ]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert trials[0]["candidate_count"] == 0


def test_untitled_two_role_movements_cannot_use_amounts_to_assign_periods() -> None:
    current = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"]),
            _row("Sử dụng dự phòng trong kỳ", ["3", "4"]),
            _row("Số dư cuối kỳ", ["600", "400"], kind="TOTAL"),
        ],
        unit="Triệu đồng",
    )
    prior = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"]),
            _row("Sử dụng dự phòng trong kỳ", ["2", "3"]),
            _row("Số dư cuối kỳ", ["500", "300"], kind="TOTAL"),
        ],
        unit="Triệu đồng",
    )
    for table in (current, prior):
        table["columns"] = table["columns"][:2]
        table["title_exact"] = None
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _customer_balance_page("(1.000)", "(800)")),
            (VERSION_2, 2, _primary_page("(100)", "(80)")),
            ("gfpstorev1:json:" + "e" * 64, 3, _movement_note([current, prior])),
        ]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert trials[0]["candidate_count"] == 0


def test_exact_root_still_cannot_let_balance_amounts_assign_untitled_periods() -> None:
    current = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"]),
            _row("Số dư cuối kỳ", ["600", "400"], kind="TOTAL"),
        ]
    )
    prior = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"]),
            _row("Số dư cuối kỳ", ["500", "300"], kind="TOTAL"),
        ]
    )
    for table in (current, prior):
        table["columns"] = table["columns"][:2]
        table["title_exact"] = None

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _customer_balance_page("(1.000)", "(800)")),
            (
                VERSION_2,
                2,
                _primary_page_with_exact_ranges("(100)", "(80)"),
            ),
            (
                "gfpstorev1:json:" + "e" * 64,
                3,
                _movement_note([current, prior]),
            ),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []


def test_exact_period_two_role_movement_derives_total_and_ignores_utilization() -> None:
    current = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"]),
            _row("Sử dụng dự phòng trong kỳ", ["3", "4"]),
            _row("Số dư cuối kỳ", ["600", "400"], kind="TOTAL"),
        ],
        title="Kỳ này năm 2025",
    )
    comparative = _movement_table(
        [
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"]),
            _row("Sử dụng dự phòng trong kỳ", ["2", "3"]),
            _row("Số dư cuối kỳ", ["500", "300"], kind="TOTAL"),
        ],
        title="Kỳ trước năm 2024",
    )
    for table in (current, comparative):
        table["columns"] = table["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [
            (
                VERSION_1,
                1,
                _primary_page_with_exact_ranges("(100)", "(80)"),
            ),
            (VERSION_2, 2, _movement_note([current, comparative])),
        ]
    )

    assert trials[0]["status"] == READY
    mapped = _mapped(trials[0])
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_PROVISION"]["values"]
    ] == [100, 80]
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_GENERAL"]["values"]
    ] == [20, 15]
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_SPECIFIC"]["values"]
    ] == [80, 65]
    assert all(
        "Sử dụng" not in source_ref["label_exact"]
        for source_ref in mapped["CUSTOMER_PROVISION"]["source_refs"]
    )


def test_customer_summary_requires_exact_period_to_select_current_not_annual() -> None:
    summary = {
        "columns": [
            {"header_path_exact": ["31/03/2025"], "value_kind": "MONEY"},
            {"header_path_exact": ["31/12/2024"], "value_kind": "MONEY"},
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dự phòng chung", ["600", "500"]),
            _row("Dự phòng cụ thể", ["400", "300"]),
            _row("Cộng", ["1.000", "800"], kind="TOTAL"),
        ],
        "title_exact": (
            "9. Dự phòng rủi ro tín dụng\n"
            "Dự phòng rủi ro cho vay khách hàng bao gồm:"
        ),
        "unit_exact": None,
    }
    current = _movement_table(
        [
            _row("Số dư đầu năm", ["580", "320"]),
            _row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"]),
            _row("Số dư cuối kỳ", ["600", "400"], kind="TOTAL"),
        ],
        title="Kỳ này",
        unit=None,
    )
    annual = _movement_table(
        [
            _row("Số dư đầu năm", ["485", "235"]),
            _row("Trích lập/(hoàn nhập) dự phòng trong năm", ["15", "65"]),
            _row("Số dư cuối năm", ["500", "300"], kind="TOTAL"),
        ],
        title="Năm trước",
        unit=None,
    )
    for table in (current, annual):
        table["columns"] = table["columns"][:2]
    note = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "tables": [summary, current, annual],
                "title_exact": "Thuyết minh báo cáo tài chính quý I năm 2025",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _indexed, legacy_trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _customer_balance_page("(1.000)", "(800)")),
            (VERSION_2, 2, _primary_page("(100)", "(70)")),
            ("gfpstorev1:json:" + "e" * 64, 3, note),
        ]
    )
    assert legacy_trials[0]["status"] == UNRESOLVED
    assert legacy_trials[0]["mappings"] == []

    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _customer_balance_page("(1.000)", "(800)")),
            (
                VERSION_2,
                2,
                _primary_page_with_exact_ranges("(100)", "(70)"),
            ),
            ("gfpstorev1:json:" + "e" * 64, 3, canonical_clone_v1(note)),
        ]
    )
    trial = trials[0]
    assert trial["status"] == READY
    mapped = _mapped(trial)
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_PROVISION"]["values"]
    ] == [100, None]
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_GENERAL"]["values"]
    ] == [20, None]
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_SPECIFIC"]["values"]
    ] == [80, None]
    receipt = trial["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]
    transposed = receipt["transposed_receipt"]
    assert transposed["comparative"] is None
    assert transposed["rule"] == (
        "EXACT_LANE_DURATION_COMPATIBILITY_REJECTS_ONLY_CONFLICTING_"
        "MOVEMENT_LANES"
    )
    assert {
        row["disposition"] for row in transposed["source_only_rows"]
    } == {
        "DETAIL_LANE_REJECTED_BY_EXACT_DURATION_SCOPE_"
        "DETAIL_DURATION_SCOPE_NOT_PROVEN"
    }


def test_direct_expense_keeps_exact_reconciled_customer_movement_breakdown() -> None:
    direct = _normal_page(
        [
            _row("Chi phí dự phòng rủi ro cho vay khách hàng", ["100", "80"]),
            _row("Hoàn nhập dự phòng hoạt động mua nợ", ["(10)", "-"]),
            _row(
                "(Hoàn nhập)/Chi phí dự phòng rủi ro cho các khoản phải thu",
                ["(5)", "(2)"],
            ),
            _row(None, ["85", "78"], kind="TOTAL"),
        ]
    )
    current = _movement_table(
        [_row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"])],
        title="Kỳ này từ 01/01/2025 đến 30/06/2025",
    )
    comparative = _movement_table(
        [_row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước từ 01/01/2024 đến 30/06/2024",
    )
    for table in (current, comparative):
        table["columns"] = table["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, direct),
            (VERSION_2, 2, _movement_note([current, comparative])),
        ]
    )
    trial = trials[0]
    assert trial["status"] == READY
    mapped = _mapped(trial)
    assert set(mapped) == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
        "FAMILY_ROOT_TOTAL",
        "OTHER_PROVISION",
        "PURCHASED_DEBT_PROVISION",
    }
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_GENERAL"]["values"]
    ] == [20, 15]
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_SPECIFIC"]["values"]
    ] == [80, 65]
    assert mapped["CUSTOMER_PROVISION"]["source_refs"][0]["label_exact"] == (
        "Chi phí dự phòng rủi ro cho vay khách hàng"
    )
    adapter = trial["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]
    assert adapter["customer_breakdown_receipt"]["observed_lane_count"] == 2
    assert adapter["source_role_coverage"]["violation_count"] == 0


def test_two_role_partial_blank_never_derives_zero() -> None:
    current = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", None])],
        title="Kỳ này từ 01/01/2025 đến 30/06/2025",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước từ 01/01/2024 đến 30/06/2024",
    )
    for table in (current, comparative):
        table["columns"] = table["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([current, comparative]))]
    )
    assert trials[0]["status"] == READY
    mapped = _mapped(trials[0])
    assert mapped["CUSTOMER_GENERAL"]["values"][0]["coefficient"] == 20
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_SPECIFIC"]["values"]
    ] == [None, 65]
    assert mapped["CUSTOMER_PROVISION"]["values"][0] == {
        "coefficient": None,
        "source_text": None,
        "state": "DERIVED_INCOMPLETE_DUE_TO_BLANK_SOURCE_CELL",
    }
    assert mapped["CUSTOMER_PROVISION"]["values"][1]["coefficient"] == 80


def test_all_blank_transposed_roles_are_omitted_not_zero_mapped() -> None:
    current = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", None])],
        title="Kỳ này từ 01/01/2025 đến 30/06/2025",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", None])],
        title="Kỳ trước từ 01/01/2024 đến 30/06/2024",
    )
    for table in (current, comparative):
        table["columns"] = table["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([current, comparative]))]
    )
    assert trials[0]["status"] == READY
    assert set(_mapped(trials[0])) == {"CUSTOMER_GENERAL"}
    coverage = trials[0]["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["source_role_coverage"]
    assert coverage["mapped_observation_count"] == 2
    assert coverage["source_only_observation_count"] == 2
    assert {
        item["disposition"]
        for item in coverage["entries"]
        if item["source_cell"]["coefficient"] is None
    } == {"SOURCE_ONLY_BLANK_ROLE_OBSERVATION_NOT_MAPPED"}


def test_bare_year_plus_relative_lane_cannot_assign_the_other_lane() -> None:
    comparative = _movement_table(
        [_row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước",
    )
    current_row = _row(
        "Trích lập/(hoàn nhập) dự phòng trong kỳ", ["20", "80"]
    )
    current_row["hierarchy_path_exact"] = ["Năm 2025", current_row["label_exact"]]
    current = _movement_table([current_row], title=None)
    for table in (comparative, current):
        table["columns"] = table["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _movement_note([comparative, current]))]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_balance_value_matches_cannot_supply_a_missing_movement_unit() -> None:
    vnd_balance = _customer_balance_page(
        "(100.000.000)", "(80.000.000)", unit="VND"
    )
    million_balance = _customer_balance_page("(100)", "(80)")
    vnd_root = _primary_page("(30.000.000)", "(20.000.000)")
    vnd_root["sections"][0]["tables"][0]["unit_exact"] = "VND"
    for column in vnd_root["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0], "VND"]
    million_root = _primary_page("(30)", "(20)")
    movement = _movement_table(
        [
            _row("Trích lập dự phòng trong kỳ", ["10", "20"]),
            _row("Số dư cuối kỳ", ["60", "40"], kind="TOTAL"),
        ],
        title="Kỳ này",
        unit=None,
    )
    movement["columns"] = movement["columns"][:2]
    _indexed, legacy_trials, _pages = _run_pages(
        [
            (VERSION_1, 1, vnd_balance),
            (VERSION_2, 2, million_balance),
            ("gfpstorev1:json:" + "e" * 64, 3, vnd_root),
            ("gfpstorev1:json:" + "f" * 64, 4, million_root),
            (
                "gfpstorev1:json:" + "1" * 64,
                5,
                _movement_note([movement]),
            ),
        ]
    )
    assert legacy_trials[0]["status"] == UNRESOLVED
    assert legacy_trials[0]["mappings"] == []

    exact_vnd_root = canonical_clone_v1(vnd_root)
    exact_million_root = canonical_clone_v1(million_root)
    for root in (exact_vnd_root, exact_million_root):
        columns = root["sections"][0]["tables"][0]["columns"]
        unit_surface = columns[0]["header_path_exact"][-1]
        columns[0]["header_path_exact"] = [
            "Kỳ này từ 01/01/2025 đến 31/03/2025",
            unit_surface,
        ]
        unit_surface = columns[1]["header_path_exact"][-1]
        columns[1]["header_path_exact"] = [
            "Kỳ trước từ 01/01/2024 đến 31/03/2024",
            unit_surface,
        ]
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, canonical_clone_v1(vnd_balance)),
            (VERSION_2, 2, canonical_clone_v1(million_balance)),
            ("gfpstorev1:json:" + "e" * 64, 3, exact_vnd_root),
            ("gfpstorev1:json:" + "f" * 64, 4, exact_million_root),
            (
                "gfpstorev1:json:" + "1" * 64,
                5,
                _movement_note([canonical_clone_v1(movement)]),
            ),
        ]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_separate_general_and_specific_period_tables_are_combined_by_lane() -> None:
    def role_section(role_label: str, values: list[str]) -> dict[str, Any]:
        return {
            "content_kind": "FINANCIAL_NOTE",
            "narratives_exact": [
                f"Biến động {role_label} cho các khoản cho vay khách hàng trong kỳ như sau:"
            ],
            "statement_type": "NOT_APPLICABLE",
            "tables": [
                {
                    "columns": [
                        {
                            "header_path_exact": [
                                "Kỳ ba tháng kết thúc ngày 31/03/2025"
                            ],
                            "value_kind": "MONEY",
                        },
                        {
                            "header_path_exact": [
                                "Kỳ ba tháng kết thúc ngày 31/03/2024"
                            ],
                            "value_kind": "MONEY",
                        },
                    ],
                    "continuation": "NONE",
                    "rows": [_row("Trích lập dự phòng trong kỳ", values)],
                    "title_exact": None,
                    "unit_exact": "Triệu VND",
                }
            ],
            "title_exact": None,
        }

    note = {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            role_section("dự phòng chung", ["20", "15"]),
            role_section("dự phòng cụ thể", ["80", "65"]),
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _primary_page("(100)", "(80)")), (VERSION_2, 2, note)]
    )
    assert trials[0]["status"] == READY
    mapped = _mapped(trials[0])
    assert [
        cell["coefficient"] for cell in mapped["CUSTOMER_PROVISION"]["values"]
    ] == [100, 80]
    assert len(mapped["CUSTOMER_PROVISION"]["source_refs"]) == 4
    assert len(mapped["CUSTOMER_GENERAL"]["source_refs"]) == 2
    assert len(mapped["CUSTOMER_SPECIFIC"]["source_refs"]) == 2
    coverage = trials[0]["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["source_role_coverage"]
    assert coverage["covered_observation_count"] == 4
    assert coverage["mapped_observation_count"] == 4
    assert coverage["violation_count"] == 0


def test_adjacent_customer_continuation_requires_exact_reporting_period() -> None:
    first = _movement_note([])
    first_table = _movement_table(
        [
            _row("Kỳ này", [None, None], kind="GROUP"),
            _row("Số dư đầu kỳ", ["1", "2"]),
        ],
        unit=None,
    )
    first_table["columns"] = first_table["columns"][:2]
    first_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    first["sections"][0]["tables"] = [first_table]
    second = _movement_note([])
    second_table = {
        "columns": [
            {"header_path_exact": [None], "value_kind": "MONEY"},
            {"header_path_exact": [None], "value_kind": "MONEY"},
        ],
        "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
        "rows": [
            _row("Trích lập dự phòng trong kỳ", ["20", "80"]),
            _row("Số dư cuối kỳ", ["21", "82"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": None,
    }
    second["sections"][0]["title_exact"] = None
    second["sections"][0]["tables"] = [second_table]
    original_second = canonical_clone_v1(second)
    _indexed, legacy_trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(100)", "(80)")),
            (VERSION_2, 2, first),
            ("gfpstorev1:json:" + "f" * 64, 3, second),
        ]
    )
    assert same_typed_json_v1(second, original_second)
    assert legacy_trials[0]["status"] == UNRESOLVED
    assert legacy_trials[0]["mappings"] == []

    _indexed, trials, _pages = _run_pages(
        [
            (
                VERSION_1,
                1,
                _primary_page_with_exact_ranges("(100)", "(80)"),
            ),
            (VERSION_2, 2, canonical_clone_v1(first)),
            (
                "gfpstorev1:json:" + "f" * 64,
                3,
                canonical_clone_v1(second),
            ),
        ]
    )
    assert trials[0]["status"] == READY
    customer = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in customer["values"]] == [100, None]
    assert customer["source_refs"][0]["hierarchy_path_exact"][0] == "Kỳ này"
    candidate = trials[0]["candidates"][0]
    assert len(candidate["component_regions"]) == 3
    receipts = candidate["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["structural_projection_receipts"]
    assert any(
        receipt["receipt_id"].startswith("gjcrpefav1:continuation-projection:")
        for receipt in receipts
    )


def test_structural_customer_continuation_ignores_unrelated_prior_narrative() -> None:
    sender = _movement_note([])
    sender_table = _movement_table(
        [
            _row("Kỳ này", [None, None, None], kind="GROUP"),
            _row("Số dư đầu kỳ", ["1", "2", "3"]),
            _row("Trích lập dự phòng trong kỳ", ["20", "80", "100"]),
        ],
        title="Đối với sự thay đổi của dự phòng rủi ro tín dụng",
        unit=None,
    )
    sender_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    sender_table["rows"][2]["hierarchy_path_exact"] = [
        "Kỳ này",
        sender_table["rows"][2]["label_exact"],
    ]
    sender["sections"][0]["title_exact"] = None
    sender["sections"][0]["narratives_exact"] = [
        "Dự phòng rủi ro chứng khoán đã được trình bày ở bảng trước",
        (
            "Các thông tin trình bày trong phần này: kỳ này bắt đầu từ "
            "01/01/2025 đến 31/03/2025; kỳ trước bắt đầu từ 01/01/2024 "
            "đến 31/12/2024."
        ),
    ]
    sender["sections"][0]["tables"] = [sender_table]

    receiver = _movement_note([])
    receiver["sections"][0]["title_exact"] = None
    receiver["sections"][0]["tables"] = [
        {
            "columns": [
                {"header_path_exact": [None], "value_kind": "MONEY"},
                {"header_path_exact": [None], "value_kind": "MONEY"},
                {"header_path_exact": [None], "value_kind": "MONEY"},
            ],
            "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
            "rows": [
                _row("Số dư cuối kỳ", ["21", "82", "103"], kind="TOTAL"),
                _row("Kỳ trước", [None, None, None], kind="GROUP"),
                _row("Số dư đầu kỳ", ["2", "3", "5"]),
                _row("Trích lập dự phòng trong kỳ", ["15", "65", "80"]),
                _row("Số dư cuối kỳ", ["17", "68", "85"], kind="TOTAL"),
            ],
            "title_exact": None,
            "unit_exact": None,
        }
    ]
    receiver["sections"][0]["tables"][0]["rows"][3][
        "hierarchy_path_exact"
    ] = [
        "Kỳ trước",
        receiver["sections"][0]["tables"][0]["rows"][3]["label_exact"],
    ]

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page_with_exact_ranges("(100)", "(80)")),
            (VERSION_2, 2, sender),
            ("gfpstorev1:json:" + "f" * 64, 3, receiver),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["CUSTOMER_PROVISION"]["values"]
    ] == [100, None]
    authority = indexed["candidate_dispositions"][0]["cluster"][
        "credit_risk_provision_expense_query_adapter_receipt"
    ]["source_authority_receipt"]
    assert any(
        cell["semantic_lane"] == "COMPARATIVE_PERIOD"
        and cell["row_ordinal"] == 4
        for cell in authority["rejected_source_cell_axis"]
    )


def test_structural_competing_owner_cannot_be_projected_as_customer() -> None:
    sender = _movement_note([])
    sender_table = _movement_table(
        [
            _row("Kỳ này", [None, None, None], kind="GROUP"),
            _row("Số dư đầu kỳ", ["1", "2", "3"]),
        ],
        title="Thay đổi dự phòng rủi ro chứng khoán",
        unit=None,
    )
    sender_table["continuation"] = "CONTINUES_ON_NEXT_PAGE"
    sender["sections"][0]["title_exact"] = None
    sender["sections"][0]["tables"] = [sender_table]

    receiver = _movement_note([])
    receiver["sections"][0]["title_exact"] = None
    receiver["sections"][0]["tables"] = [
        {
            "columns": [
                {"header_path_exact": [None], "value_kind": "MONEY"},
                {"header_path_exact": [None], "value_kind": "MONEY"},
                {"header_path_exact": [None], "value_kind": "MONEY"},
            ],
            "continuation": "CONTINUES_FROM_PREVIOUS_PAGE",
            "rows": [
                _row("Trích lập dự phòng trong kỳ", ["20", "80", "100"]),
                _row("Số dư cuối kỳ", ["21", "82", "103"], kind="TOTAL"),
            ],
            "title_exact": None,
            "unit_exact": None,
        }
    ]

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page_with_exact_ranges("(100)", "(80)")),
            (VERSION_2, 2, sender),
            ("gfpstorev1:json:" + "f" * 64, 3, receiver),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == NOT_OBSERVED
    assert trials[0]["status"] == NOT_OBSERVED
    assert trials[0]["mappings"] == []


def test_primary_amount_cannot_choose_net_from_gross_and_reversal_variants() -> None:
    rows = []
    for year, gross, reversal in (
        (2025, ["20", "80", "100"], ["(2)", "(8)", "(10)"]),
        (2024, ["15", "65", "80"], ["(1)", "(4)", "(5)"]),
    ):
        for label, values in (
            ("Dự phòng rủi ro trích lập trong năm", gross),
            ("Số dự phòng hoàn nhập trong năm", reversal),
        ):
            row = _row(label, values)
            row["hierarchy_path_exact"] = [f"Năm {year}", label]
            rows.append(row)
    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(90)", "(75)")),
            (VERSION_2, 2, _movement_note([_movement_table(rows)])),
        ]
    )
    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []
    assert trials[0]["reasons"] == ["F37_TRANSPOSED_PRESENTATION_NOT_UNIQUE"]


def test_primary_amount_cannot_choose_gross_over_visible_reversal_variant() -> None:
    def table(year: int, gross: list[str], reversal: list[str]) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong kỳ", gross),
                _row("Số hoàn nhập dự phòng trong kỳ", reversal),
            ],
            title=f"Thay đổi dự phòng năm {year}",
        )

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(100)", "(80)")),
            (
                VERSION_2,
                2,
                _movement_note(
                    [
                        table(2025, ["20", "80", "100"], ["(2)", "(8)", "(10)"]),
                        table(2024, ["15", "65", "80"], ["(1)", "(4)", "(5)"]),
                    ]
                ),
            ),
        ]
    )
    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []
    assert trials[0]["reasons"] == ["F37_TRANSPOSED_PRESENTATION_NOT_UNIQUE"]


def test_exact_gross_primary_label_selects_gross_without_amount_routing() -> None:
    def table(year: int, gross: list[str], reversal: list[str]) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong năm", gross),
                _row("Số hoàn nhập dự phòng trong năm", reversal),
            ],
            title=(
                f"Thay đổi dự phòng từ ngày 01/01/{year} "
                f"đến ngày 31/12/{year}"
            ),
        )

    primary = _primary_page_with_exact_ranges(
        "(90)",
        "(75)",
        current_end="31/12/2025",
        comparative_end="31/12/2024",
    )
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (
                VERSION_2,
                2,
                _movement_note(
                    [
                        table(2025, ["20", "80", "100"], ["(2)", "(8)", "(10)"]),
                        table(2024, ["15", "65", "80"], ["(1)", "(4)", "(5)"]),
                    ]
                ),
            ),
        ]
    )

    assert trials[0]["status"] == READY
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["CUSTOMER_PROVISION"]["values"]
    ] == [100, 80]


def test_exact_combined_primary_label_selects_net_without_amount_routing() -> None:
    def table(year: int, gross: list[str], reversal: list[str]) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong năm", gross),
                _row("Số hoàn nhập dự phòng trong năm", reversal),
            ],
            title=(
                f"Thay đổi dự phòng từ ngày 01/01/{year} "
                f"đến ngày 31/12/{year}"
            ),
        )

    primary = _primary_page_with_exact_ranges(
        "(100)",
        "(80)",
        current_end="31/12/2025",
        comparative_end="31/12/2024",
    )
    combined_label = "Chi phí/(Hoàn nhập) dự phòng rủi ro tín dụng"
    primary["sections"][0]["tables"][0]["rows"][0]["label_exact"] = combined_label
    primary["sections"][0]["tables"][0]["rows"][0][
        "hierarchy_path_exact"
    ] = [combined_label]
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (
                VERSION_2,
                2,
                _movement_note(
                    [
                        table(2025, ["20", "80", "100"], ["(2)", "(8)", "(10)"]),
                        table(2024, ["15", "65", "80"], ["(1)", "(4)", "(5)"]),
                    ]
                ),
            ),
        ]
    )

    assert trials[0]["status"] == READY
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["CUSTOMER_PROVISION"]["values"]
    ] == [90, 75]


def _annual_layout_bound_movement_page() -> dict[str, Any]:
    snapshot = {
        "columns": [
            {"header_path_exact": ["31/12/2025"], "value_kind": "MONEY"}
        ],
        "continuation": "NONE",
        "rows": [
            _row("Dự phòng cụ thể", ["625"]),
            _row("Dự phòng chung", ["939"]),
            _row(None, ["1.564"], kind="TOTAL"),
        ],
        "title_exact": None,
        "unit_exact": "Triệu đồng",
    }

    def movement(gross: list[str], reversal: list[str]) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong kỳ", gross),
                _row("Số hoàn nhập dự phòng trong kỳ", reversal),
            ],
            title=None,
        )

    return {
        "completion": {
            "all_relevant_content_transcribed": True,
            "uncertainty_exact": [],
        },
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [
                    "Chi tiết số dư dự phòng tại ngày 31 tháng 12 năm 2025 như sau:",
                    "Thay đổi dự phòng rủi ro tín dụng đến hết Quý 4 năm 2025 bao gồm các khoản sau:",
                    "Thay đổi dự phòng rủi ro tín dụng trong năm 2024 bao gồm các khoản sau:",
                ],
                "statement_type": "NOT_APPLICABLE",
                "tables": [
                    snapshot,
                    movement(["173", "153", "326"], ["(56)", "(28)", "(84)"]),
                    movement(["185", "90", "275"], ["(103)", "(20)", "(123)"]),
                ],
                "title_exact": "Thay đổi (tăng/giảm) của dự phòng rủi ro tín dụng",
            }
        ],
        "status": "FINANCIAL_NOTE_CONTENT",
    }


def test_exact_same_section_narrative_table_layout_binds_annual_gross_lanes() -> None:
    primary = _primary_page_with_exact_ranges(
        "(999)",
        "(888)",
        current_end="31/12/2025",
        comparative_end="31/12/2024",
    )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, _annual_layout_bound_movement_page())]
    )

    assert trials[0]["status"] == READY
    customer = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in customer["values"]] == [326, 275]
    assert customer["state"].endswith("DIRECT_GROSS_PROVISION")


@pytest.mark.parametrize(
    "variant",
    ["SWAPPED", "MISSING", "EXTRA", "CONFLICTING", "COMPETING_TABLE"],
)
def test_annual_narrative_table_layout_fails_closed_when_not_exact(
    variant: str,
) -> None:
    note = _annual_layout_bound_movement_page()
    section = note["sections"][0]
    if variant == "SWAPPED":
        section["narratives_exact"][1:] = reversed(
            section["narratives_exact"][1:]
        )
    elif variant == "MISSING":
        section["narratives_exact"].pop()
    elif variant == "EXTRA":
        section["narratives_exact"].append("Thông tin bổ sung như sau:")
    elif variant == "CONFLICTING":
        section["narratives_exact"][1] = (
            "Thay đổi dự phòng rủi ro tín dụng trong năm 2023 bao gồm các khoản sau:"
        )
    else:
        section["tables"].append(canonical_clone_v1(section["tables"][-1]))
    primary = _primary_page_with_exact_ranges(
        "(999)",
        "(888)",
        current_end="31/12/2025",
        comparative_end="31/12/2024",
    )

    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, note)]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_direct_expense_maps_reconciled_breakdown_and_types_duplicate_total_source_only() -> None:
    direct = _normal_page(
        [
            _row("Trích lập dự phòng cho vay khách hàng", ["100", "80"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ]
    )
    movement = _movement_note(
        [
            _movement_table(
                [_row("Dự phòng rủi ro trích lập trong kỳ", ["20", "80", "100"])],
                title="Kỳ này từ 01/01/2025 đến 30/06/2025",
            ),
            _movement_table(
                [_row("Dự phòng rủi ro trích lập trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước từ 01/01/2024 đến 30/06/2024",
            ),
        ]
    )
    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, direct), (VERSION_2, 2, movement)]
    )
    candidate = trials[0]["candidates"][0]
    coverage = candidate["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["source_role_coverage"]
    assert coverage["covered_observation_count"] == 6
    assert coverage["mapped_observation_count"] == 4
    assert coverage["source_only_observation_count"] == 2
    assert coverage["violation_count"] == 0
    assert {
        entry["role"]
        for entry in coverage["entries"]
        if entry["disposition"] == "MAPPED_FROM_EXACT_SOURCE_OBSERVATION"
    } == {"CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"}
    assert {
        entry["role"]
        for entry in coverage["entries"]
        if entry["disposition"].startswith("SOURCE_ONLY_")
    } == {"CUSTOMER_PROVISION"}


def test_narrative_and_amount_cannot_choose_among_gross_net_period_variants() -> None:
    current = _movement_table(
        [
            _row("Dự phòng rủi ro trích lập trong kỳ", ["20", "80", "100"]),
            _row("Số hoàn nhập dự phòng trong kỳ", ["(2)", "(8)", "(10)"]),
        ]
    )
    prior_annual = _movement_table(
        [
            _row("Dự phòng rủi ro trích lập trong kỳ", ["15", "65", "80"]),
            _row("Số hoàn nhập dự phòng trong kỳ", ["(1)", "(4)", "(5)"]),
        ]
    )
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(100)", "(61)")),
            (
                VERSION_2,
                2,
                _movement_note(
                    [current, prior_annual],
                    narratives=[
                        "Thay đổi dự phòng đến hết Quý 3 năm 2025",
                        "Thay đổi dự phòng trong năm 2024",
                    ],
                ),
            ),
        ]
    )
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []


def test_exact_ytd_combined_action_excludes_noncomparable_prior_annual_lane() -> None:
    current = _movement_table(
        [
            _row(
                "Trích lập/(hoàn nhập) dự phòng trong kỳ",
                ["20", "80", "100"],
            )
        ],
        title="Lũy kế từ 01/01/2025 đến 30/09/2025",
    )
    prior_annual = _movement_table(
        [
            _row(
                "Trích lập/(hoàn nhập) dự phòng trong năm",
                ["15", "65", "80"],
            )
        ],
        title="Năm 2024",
    )
    primary = _primary_page_with_exact_ranges(
        "(100)",
        "(61)",
        current_end="30/09/2025",
        comparative_end="30/09/2024",
    )
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (VERSION_2, 2, _movement_note([current, prior_annual])),
        ]
    )

    assert trials[0]["status"] == READY
    mapped = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in mapped["values"]] == [100, None]
    assert mapped["values"][1]["state"] == "UNOBSERVED_SOURCE_LANE"
    source_only = trials[0]["candidates"][0]["closure_receipt"][
        "source_only_unmapped_rows"
    ]
    assert {item["row_ordinal"] for item in source_only} == {1}


def test_bare_year_tables_without_primary_root_are_unresolved() -> None:
    note = _movement_note(
        [
            _movement_table(
                [_row("Trích lập trong năm", ["20", "80", "100"])],
                title="Năm 2025",
            ),
            _movement_table(
                [_row("Trích lập trong năm", ["15", "65", "80"])],
                title="Năm 2024",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages([(VERSION_1, 1, note)])
    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_exact_semantic_detail_scopes_without_primary_root_map_observed_roles() -> None:
    note = _movement_note(
        [
            _movement_table(
                [_row("Trích lập trong kỳ", ["20", "80", "100"])],
                title="Kỳ này từ 01/01/2025 đến 30/06/2025",
            ),
            _movement_table(
                [_row("Trích lập trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước từ 01/01/2024 đến 30/06/2024",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages([(VERSION_1, 1, note)])
    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    assert set(_mapped(trials[0])) == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
    }


def test_positive_unitless_transposed_owner_is_typed_u_not_n() -> None:
    note = _movement_note(
        [
            _movement_table(
                [_row("Trích lập trong kỳ", ["20", "80", "100"])],
                unit=None,
            )
        ]
    )
    indexed, trials, _pages = _run_pages([(VERSION_1, 1, note)])
    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []


def test_visible_gross_net_movement_ambiguity_is_unresolved_not_unobserved() -> None:
    def table(year: int) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong kỳ", ["20", "80", "100"]),
                _row("Số hoàn nhập dự phòng trong kỳ", ["(2)", "(8)", "(10)"]),
            ],
            title=f"Sáu tháng kết thúc năm {year}",
        )

    primary = _primary_page("(103)", "(83)")
    primary["sections"][0]["tables"][0]["rows"][0]["label_exact"] = (
        "Kết quả dự phòng rủi ro tín dụng"
    )
    primary["sections"][0]["tables"][0]["rows"][0][
        "hierarchy_path_exact"
    ] = ["Kết quả dự phòng rủi ro tín dụng"]
    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (VERSION_2, 2, _movement_note([table(2025), table(2024)])),
        ]
    )
    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["candidate_count"] == 0
    assert trials[0]["mappings"] == []
    authority = indexed["candidate_dispositions"][0]["cluster"][
        "credit_risk_provision_expense_query_adapter_receipt"
    ]["source_authority_receipt"]
    assert authority["decision"] == UNRESOLVED
    assert len(authority["rejected_source_cell_axis"]) == 12


def test_primary_root_carrier_without_detail_remains_not_observed() -> None:
    indexed, trials, pages = _run_pages([(VERSION_1, 1, _primary_page("(100)", "(80)"))])
    assert indexed["candidate_dispositions"][0]["disposition"] == NOT_OBSERVED
    assert trials[0]["status"] == NOT_OBSERVED
    assert trials[0]["mappings"] == []
    coverage = build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert coverage["violation_count"] == 0
    assert {
        item["coverage"] for item in coverage["source_row_axis"]
    } == {
        "PRIMARY_STATEMENT_ROOT_CARRIER_ONLY_MISSING_DISCLOSURE_OWNER_PERIOD_OR_UNIT"
    }


def test_source_row_coverage_fails_closed_when_selected_role_is_unmapped() -> None:
    rows = [
        _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
        _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
        _row(None, ["100", "80"], kind="TOTAL"),
    ]
    indexed, trials, pages = _run_pages([(VERSION_1, 1, _normal_page(rows))])
    stripped = canonical_clone_v1(trials)
    stripped[0]["mappings"] = []
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="source-row coverage has 3 violation",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=stripped,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_source_row_coverage_scans_raw_unconfigured_duration_row() -> None:
    page = _normal_page(
        [
            _row(
                "Trích lập dự phòng rủi ro cho dư nợ bán lẻ",
                ["20", "15"],
            )
        ]
    )
    indexed, trials, pages = _run_pages([(VERSION_1, 1, page)])
    assert trials[0]["status"] == NOT_OBSERVED
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=trials,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_source_row_coverage_types_secondary_root_presentations() -> None:
    normal = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ]
    )
    multidimensional = _normal_page(
        [_row(OWNER, ["20", "30", "50"], kind="TOTAL")],
        columns=[
            {"header_path_exact": ["Miền Bắc"], "value_kind": "MONEY"},
            {"header_path_exact": ["Miền Nam"], "value_kind": "MONEY"},
            {"header_path_exact": ["Tổng cộng"], "value_kind": "MONEY"},
        ],
    )
    multidimensional["sections"][0]["title_exact"] = "Báo cáo bộ phận"
    restructuring = _normal_page(
        [
            _row(OWNER, ["40", "30"]),
            _row("Tổng cộng chi phí thực hiện theo PACCL", ["50", "40"], kind="TOTAL"),
        ]
    )
    restructuring["sections"][0]["title_exact"] = "Thông tin khác"
    restructuring["sections"][0]["narratives_exact"] = [
        "Các nội dung theo phương án cơ cấu lại được thực hiện trong kỳ."
    ]
    indexed, trials, pages = _run_pages(
        [
            (VERSION_1, 1, normal),
            (VERSION_2, 2, multidimensional),
            ("gfpstorev1:json:" + "e" * 64, 3, restructuring),
        ]
    )
    coverage = build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    assert coverage["violation_count"] == 0
    assert coverage["source_row_disposition_counts"] == {
        "MAPPED_EXACT_SOURCE_ROLE_ROW": 2,
        "SECONDARY_MULTIDIMENSIONAL_OR_REGULATORY_FAMILY_ROOT_"
        "PRESENTATION_SOURCE_ONLY": 1,
        "SECONDARY_RESTRUCTURING_PLAN_SUBSET_FAMILY_ROOT_SOURCE_ONLY": 1,
    }


def test_source_row_coverage_does_not_hide_one_lane_family_root() -> None:
    normal = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ]
    )
    one_lane = _normal_page(
        [_row(OWNER, ["100"], kind="TOTAL")],
        columns=[
            {"header_path_exact": ["Kỳ này"], "value_kind": "MONEY"},
        ],
    )
    one_lane["sections"][0]["title_exact"] = "Thông tin bổ sung"
    indexed, trials, pages = _run_pages(
        [(VERSION_1, 1, normal), (VERSION_2, 2, one_lane)]
    )
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="source-row coverage has 1 violation",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=trials,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_authenticated_dash_repair_is_content_bound_and_clone_only() -> None:
    compiled = _compiled()
    repair = compiled["credit_risk_provision_expense_source_repairs"][0]
    locator = repair["locator"]
    page = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["1", "1"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["1", "1"]),
            _row("Chi phí dự phòng trái phiếu đặc biệt VAMC", ["1", "1"]),
            _row("Trích lập/(Hoàn nhập) dự phòng cho hoạt động mua nợ", ["1", None]),
            _row("Tổng", ["4", "3"], kind="TOTAL"),
        ]
    )
    page["sections"].insert(
        0,
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": None,
        },
    )
    original = canonical_clone_v1(page)
    projected, receipts = _apply_document_repairs(
        pages={locator["page_json_version_id"]: page},
        source_sha256=repair["source_sha256"],
        compiled_specs=compiled,
    )
    assert same_typed_json_v1(page, original)
    assert projected[locator["page_json_version_id"]]["sections"][1]["tables"][0][
        "rows"
    ][3]["values_exact"][1] == "-"
    assert len(receipts) == 1
    drifted = canonical_clone_v1(page)
    drifted["sections"][1]["tables"][0]["rows"][3]["values_exact"][1] = "0"
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="before image drifted",
    ):
        _apply_document_repairs(
            pages={locator["page_json_version_id"]: drifted},
            source_sha256=repair["source_sha256"],
            compiled_specs=compiled,
        )


def test_authenticated_row_label_repair_binds_label_and_hierarchy_clone_only() -> None:
    compiled = _compiled()
    repair = next(
        item
        for item in compiled["credit_risk_provision_expense_source_repairs"]
        if item["repair_kind"] == "ROW_LABEL_PDF_VISIBLE_EXACT"
    )
    locator = repair["locator"]
    row = _row(repair["before_label_exact"], ["15", "(280)", "(280.031)"])
    page = _normal_page([_row("filler", ["1", "1"])] * 4 + [row])
    page["sections"].insert(
        0,
        {
            "content_kind": "NARRATIVE",
            "narratives_exact": [],
            "statement_type": "NOT_APPLICABLE",
            "tables": [],
            "title_exact": None,
        },
    )
    original = canonical_clone_v1(page)
    projected, receipts = _apply_document_repairs(
        pages={locator["page_json_version_id"]: page},
        source_sha256=repair["source_sha256"],
        compiled_specs=compiled,
    )
    repaired = projected[locator["page_json_version_id"]]["sections"][1]["tables"][0][
        "rows"
    ][4]
    assert same_typed_json_v1(page, original)
    assert repaired["label_exact"] == repair["after_label_exact"]
    assert repaired["hierarchy_path_exact"] == repair["after_hierarchy_path_exact"]
    assert len(receipts) == 1
    drifted = canonical_clone_v1(page)
    drifted["sections"][1]["tables"][0]["rows"][4]["hierarchy_path_exact"] = [
        "different"
    ]
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="before image drifted",
    ):
        _apply_document_repairs(
            pages={locator["page_json_version_id"]: drifted},
            source_sha256=repair["source_sha256"],
            compiled_specs=compiled,
        )


def test_normal_root_follows_semantic_lanes_after_full_column_reversal() -> None:
    page = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ]
    )
    table = page["sections"][0]["tables"][0]
    table["columns"].reverse()
    for row in table["rows"]:
        row["values_exact"].reverse()

    _indexed, trials, _pages = _run_pages([(VERSION_1, 1, page)])

    mapped = _mapped(trials[0])
    assert [cell["coefficient"] for cell in mapped["CUSTOMER_GENERAL"]["values"]] == [
        20,
        15,
    ]
    assert [cell["coefficient"] for cell in mapped["CUSTOMER_SPECIFIC"]["values"]] == [
        80,
        65,
    ]
    root = mapped["FAMILY_ROOT_TOTAL"]
    assert [cell["coefficient"] for cell in root["values"]] == [100, 80]
    assert root["source_refs"][0]["money_column_ordinals"] == [2, 1]


def _quarter_primary_page(*, ytd: bool = False) -> dict[str, Any]:
    page = _primary_page("(100)", "(80)")
    columns = page["sections"][0]["tables"][0]["columns"]
    for column, year in zip(columns, (2026, 2025), strict=True):
        column["header_path_exact"] = [
            (
                f"Số lũy kế từ đầu năm đến cuối Q2.{year}"
                if ytd
                else f"Quý 2.{year}"
            ),
            "Triệu đồng",
        ]
    return page


def _quarter_movement_page() -> dict[str, Any]:
    return _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Quý 2.2026",
            ),
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
                title="Quý 2.2025",
            ),
        ]
    )


def test_quarter_detail_cannot_bind_ytd_primary_root() -> None:
    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _quarter_primary_page(ytd=True)),
            (VERSION_2, 2, _quarter_movement_page()),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_DETAIL_PRIMARY_DURATION_SCOPE_CONFLICT" in trials[0]["reasons"]


@pytest.mark.parametrize("month_count", [1, 2, 5, 7, 11, 12])
def test_arbitrary_elapsed_month_count_is_preserved(month_count: int) -> None:
    scope = _family37_period_scope_v1(
        f"Lũy kế {month_count} tháng từ đầu năm 2025",
        semantic_role="CURRENT_PERIOD",
    )

    assert scope["basis"] == "ELAPSED_FROM_YEAR_START"
    assert scope["elapsed_month_count"] == month_count


@pytest.mark.parametrize("surface", ["0 tháng", "13 tháng", "-2 tháng", "− 2 tháng"])
def test_unsupported_explicit_month_count_is_not_unknown(surface: str) -> None:
    scope = _family37_period_scope_v1(
        f"Lũy kế từ đầu năm trong {surface} năm 2025",
        semantic_role="CURRENT_PERIOD",
    )

    assert scope["basis"] == "UNSUPPORTED_EXPLICIT_DURATION"
    assert scope["reasons"] == ["UNSUPPORTED_EXPLICIT_MONTH_COUNT"]


def test_calendar_day_before_vietnamese_month_name_is_not_a_duration_count() -> None:
    scope = _family37_period_scope_v1(
        [
            "Lũy kế từ đầu kỳ đến ngày",
            "31/12/2025",
            "Quý 4 kết thúc ngày 31 tháng 12 năm 2025",
        ],
        semantic_role="CURRENT_PERIOD",
    )

    assert scope["basis"] == "ELAPSED_FROM_YEAR_START"
    assert scope["elapsed_month_count"] == 12
    assert scope["reasons"] == []


@pytest.mark.parametrize(
    ("detail_start", "expected_current"),
    [("01/02/2025", 100), ("01/03/2025", None)],
)
def test_exact_date_range_requires_identical_endpoints(
    detail_start: str, expected_current: int | None
) -> None:
    current = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title=f"Từ ngày {detail_start} đến ngày 30/06/2025",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
        title="Từ ngày 01/02/2024 đến ngày 30/06/2024",
    )
    primary = _primary_page_with_exact_ranges(
        "(100)",
        "(80)",
        current_start="01/02/2025",
        current_end="30/06/2025",
        comparative_start="01/02/2024",
        comparative_end="30/06/2024",
    )

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (VERSION_2, 2, _movement_note([current, comparative])),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    customer = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in customer["values"]] == [
        expected_current,
        80,
    ]
    if expected_current is None:
        authority = indexed["candidate_dispositions"][0]["cluster"][
            "credit_risk_provision_expense_query_adapter_receipt"
        ]["source_authority_receipt"]
        assert any(
            item["semantic_lane"] == "CURRENT_PERIOD"
            and item["accepted"] is False
            and item["compatibility"] == "EXACT_DATE_RANGE_ENDPOINT_CONFLICT"
            for item in authority["period_authority_axis"]
        )


def test_both_exact_date_range_endpoint_conflicts_are_unresolved() -> None:
    current = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Từ ngày 01/03/2025 đến ngày 30/06/2025",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
        title="Từ ngày 01/03/2024 đến ngày 30/06/2024",
    )
    primary = _primary_page_with_exact_ranges(
        "(100)",
        "(80)",
        current_start="01/02/2025",
        current_end="30/06/2025",
        comparative_start="01/02/2024",
        comparative_end="30/06/2024",
    )

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, primary),
            (VERSION_2, 2, _movement_note([current, comparative])),
        ]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_primary_section_narrative_cannot_retroactively_authorize_bare_headers() -> None:
    primary = _primary_page("(100)", "(80)")
    primary["sections"][0]["narratives_exact"] = [
        "Phần sau trình bày kỳ từ 01/01/2025 đến 31/03/2025"
    ]
    movement = _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Kỳ này",
            )
        ]
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, movement)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []


def test_matching_quarter_detail_keeps_semantic_root_after_reversal() -> None:
    primary = _quarter_primary_page()
    table = primary["sections"][0]["tables"][0]
    table["columns"].reverse()
    table["rows"][0]["values_exact"].reverse()

    _indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, _quarter_movement_page())]
    )

    assert trials[0]["status"] == READY
    root = _mapped(trials[0])["FAMILY_ROOT_TOTAL"]
    assert [cell["coefficient"] for cell in root["values"]] == [-100, -80]
    assert root["source_refs"][0]["money_column_ordinals"] == [2, 1]


def test_valid_normal_next_from_pair_is_one_two_region_candidate() -> None:
    sender = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
        ]
    )
    sender["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_ON_NEXT_PAGE"
    )
    receiver = _normal_page([_row(None, ["100", "80"], kind="TOTAL")])
    receiver["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_FROM_PREVIOUS_PAGE"
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, sender), (VERSION_2, 2, receiver)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    assert len(trials[0]["candidates"][0]["component_regions"]) == 2
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["FAMILY_ROOT_TOTAL"]["values"]
    ] == [100, 80]


def test_page_json_mapping_insertion_order_cannot_change_authority() -> None:
    def fixture() -> list[tuple[str, int, dict[str, Any]]]:
        sender = _normal_page(
            [
                _row(
                    "Trích lập dự phòng chung cho vay khách hàng",
                    ["20", "15"],
                ),
                _row(
                    "Trích lập dự phòng cụ thể cho vay khách hàng",
                    ["80", "65"],
                ),
            ]
        )
        sender["sections"][0]["tables"][0]["continuation"] = (
            "CONTINUES_ON_NEXT_PAGE"
        )
        receiver = _normal_page([_row(None, ["100", "80"], kind="TOTAL")])
        receiver["sections"][0]["tables"][0]["continuation"] = (
            "CONTINUES_FROM_PREVIOUS_PAGE"
        )
        return [(VERSION_1, 1, sender), (VERSION_2, 2, receiver)]

    indexed, trials, _pages = _run_pages(fixture())
    reversed_indexed, reversed_trials, _reversed_pages = _run_pages(
        fixture(), reverse_page_map=True
    )

    assert same_typed_json_v1(indexed, reversed_indexed)
    assert same_typed_json_v1(trials, reversed_trials)


@pytest.mark.parametrize(
    "marker", ["CONTINUES_ON_NEXT_PAGE", "BOTH"]
)
def test_unclosed_positive_normal_population_is_typed_unresolved(marker: str) -> None:
    page = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["100", "80"], kind="TOTAL"),
        ]
    )
    page["sections"][0]["tables"][0]["continuation"] = marker

    indexed, trials, _pages = _run_pages([(VERSION_1, 1, page)])

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_SOURCE_CONTINUATION_NOT_CLOSED" in trials[0]["reasons"]


def test_positive_owner_with_invalid_lane_axis_is_u_not_n() -> None:
    page = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row(None, ["20", "15"], kind="TOTAL"),
        ],
        columns=[
            {"header_path_exact": ["Giá trị A"], "value_kind": "MONEY"},
            {"header_path_exact": ["Giá trị B"], "value_kind": "MONEY"},
        ],
    )

    indexed, trials, _pages = _run_pages([(VERSION_1, 1, page)])

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert "F37_POSITIVE_OWNER_WITHOUT_SAFE_SEMANTIC_LANES" in trials[0]["reasons"]


def _resealed_disposition(
    indexed: dict[str, Any], *, status: str
) -> dict[str, Any]:
    cluster = canonical_clone_v1(indexed["candidate_dispositions"][0]["cluster"])
    receipt = cluster["credit_risk_provision_expense_query_adapter_receipt"]
    receipt_material = {key: value for key, value in receipt.items() if key != "receipt_id"}
    receipt_material["query_kind"] = "FORGED_COHERENT_" + status
    cluster["credit_risk_provision_expense_query_adapter_receipt"] = {
        **receipt_material,
        "receipt_id": "gjcrpefav1:query:"
        + canonical_json_sha256_v1(receipt_material),
    }
    if status == READY:
        cluster["reasons"] = []
    elif status == UNRESOLVED:
        cluster["component_regions"] = []
        cluster["owner_receipt"] = None
        cluster["reasons"] = ["F37_FORGED_SOURCE_AUTHORITY"]
    else:
        cluster["component_regions"] = []
        cluster["owner_receipt"] = None
        cluster["reasons"] = []
    cluster["status"] = status
    material = {key: value for key, value in cluster.items() if key != "cluster_id"}
    cluster["cluster_id"] = "gjmthfcv1:cluster:" + canonical_json_sha256_v1(material)
    return build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1(
        selected_document_axis=indexed["selected_document_axis"],
        selected_page_axis=indexed["selected_page_axis"],
        document_clusters=[cluster],
        query_policy_sha256=canonical_json_sha256_v1(_compiled()["query_policy"]),
    )


@pytest.mark.parametrize("status", [READY, UNRESOLVED, NOT_OBSERVED])
def test_trial_builder_recomputes_ready_u_n_source_authority(status: str) -> None:
    indexed, _trials, pages = _run_pages(
        [
            (
                VERSION_1,
                1,
                _normal_page(
                    [
                        _row(
                            "Trích lập dự phòng chung cho vay khách hàng",
                            ["20", "15"],
                        ),
                        _row(
                            "Trích lập dự phòng cụ thể cho vay khách hàng",
                            ["80", "65"],
                        ),
                        _row(None, ["100", "80"], kind="TOTAL"),
                    ]
                ),
            )
        ]
    )
    forged = _resealed_disposition(indexed, status=status)

    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="source authority disposition drifted",
    ):
        build_gemini_json_credit_risk_provision_expense_trials_v1(
            indexed_query_evidence=forged,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_page_payload_mutation_after_indexing_is_rejected_for_trials() -> None:
    indexed, _trials, pages = _run_pages(
        [
            (
                VERSION_1,
                1,
                _normal_page(
                    [
                        _row(
                            "Trích lập dự phòng chung cho vay khách hàng",
                            ["20", "15"],
                        ),
                        _row(None, ["20", "15"], kind="TOTAL"),
                    ]
                ),
            )
        ]
    )
    drifted = {
        ordinal: canonical_clone_v1(document_pages)
        for ordinal, document_pages in pages.items()
    }
    drifted[1][VERSION_1]["sections"][0]["tables"][0]["rows"][0][
        "values_exact"
    ][0] = "999"

    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="source authority disposition drifted",
    ):
        build_gemini_json_credit_risk_provision_expense_trials_v1(
            indexed_query_evidence=indexed,
            page_json_by_document=drifted,
            compiled_specs=_compiled(),
        )


def test_ready_normal_group_cannot_mask_second_positive_open_population() -> None:
    complete = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row(None, ["20", "15"], kind="TOTAL"),
        ]
    )
    orphan = _normal_page(
        [
            _row("Trích lập dự phòng cụ thể cho vay khách hàng", ["80", "65"]),
            _row(None, ["80", "65"], kind="TOTAL"),
        ]
    )
    orphan["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_ON_NEXT_PAGE"
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, complete), (VERSION_2, 2, orphan)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_SOURCE_CONTINUATION_NOT_CLOSED" in trials[0]["reasons"]


def test_normal_next_cannot_inherit_foreign_from_total() -> None:
    sender = _normal_page(
        [_row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"])]
    )
    sender["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_ON_NEXT_PAGE"
    )
    foreign = _normal_page([_row(None, ["20", "15"], kind="TOTAL")])
    foreign["sections"][0]["title_exact"] = "Thu nhập lãi thuần"
    foreign["sections"][0]["tables"][0]["title_exact"] = "Bảng thu nhập khác"
    foreign["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_FROM_PREVIOUS_PAGE"
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, sender), (VERSION_2, 2, foreign)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    authority = indexed["candidate_dispositions"][0]["cluster"][
        "credit_risk_provision_expense_query_adapter_receipt"
    ]["source_authority_receipt"]
    assert "CONTINUATION_SEMANTIC_CONFLICT" in {
        item["reason"] for item in authority["normal_continuation_rejection_axis"]
    }


def test_primary_statement_next_marker_does_not_poison_detail_population() -> None:
    primary = _primary_page("(20)", "(15)")
    primary["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_ON_NEXT_PAGE"
    )
    note = _normal_page(
        [
            _row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"]),
            _row(None, ["20", "15"], kind="TOTAL"),
        ]
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, note)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY


def test_normal_continuation_requires_exact_source_period_compatibility() -> None:
    sender = _normal_page(
        [_row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"])]
    )
    sender["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_ON_NEXT_PAGE"
    )
    receiver = _normal_page(
        [_row(None, ["20", "15"], kind="TOTAL")],
        columns=[
            {"header_path_exact": ["Quý 2.2026"], "value_kind": "MONEY"},
            {"header_path_exact": ["Quý 2.2025"], "value_kind": "MONEY"},
        ],
    )
    receiver["sections"][0]["tables"][0]["continuation"] = (
        "CONTINUES_FROM_PREVIOUS_PAGE"
    )

    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, sender), (VERSION_2, 2, receiver)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_SOURCE_CONTINUATION_NOT_CLOSED" in trials[0]["reasons"]


def test_direct_typed_u_requires_exact_owned_regions_and_has_zero_mappings() -> None:
    page = _normal_page(
        [_row("Trích lập dự phòng chung cho vay khách hàng", ["20", "15"])],
        columns=[
            {"header_path_exact": ["Giá trị A"], "value_kind": "MONEY"},
            {"header_path_exact": ["Giá trị B"], "value_kind": "MONEY"},
        ],
    )
    indexed, _trials, pages = _run_pages([(VERSION_1, 1, page)])
    cluster = indexed["candidate_dispositions"][0]["cluster"]
    regions = cluster["credit_risk_provision_expense_query_adapter_receipt"][
        "source_authority_receipt"
    ]["owned_region_axis"]
    receipt = build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
        regions
    )

    candidate = evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
        regions=regions,
        page_json_by_version=pages[1],
        selected_page_axis=indexed["selected_page_axis"],
        compiled_specs=_compiled(),
        query_receipt=receipt,
    )

    assert candidate["status"] == UNRESOLVED
    assert candidate["component_regions"] == regions
    assert candidate["mappings"] == []
    assert candidate["reasons"] == [
        "F37_POSITIVE_OWNER_WITHOUT_SAFE_SEMANTIC_LANES"
    ]
    drifted = canonical_clone_v1(regions)
    drifted[0]["component_roles"] = []
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="direct candidate regions drifted",
    ):
        evaluate_gemini_json_credit_risk_provision_expense_family_cluster_v1(
            regions=drifted,
            page_json_by_version=pages[1],
            selected_page_axis=indexed["selected_page_axis"],
            compiled_specs=_compiled(),
            query_receipt=(
                build_gemini_json_multitable_hierarchical_region_query_receipt_v1(
                    drifted
                )
            ),
        )


def _partial_period_lane_fixture() -> list[tuple[str, int, dict[str, Any]]]:
    current = _movement_table(
        [
            _row(
                "Trích lập/(hoàn nhập) dự phòng trong kỳ",
                ["20", "80", "100"],
            )
        ],
        title="Kỳ này",
    )
    comparative = _movement_table(
        [
            _row(
                "Trích lập/(hoàn nhập) dự phòng trong năm",
                ["15", "65", "80"],
            )
        ],
        title="Năm trước",
    )
    return [
        (VERSION_1, 1, _quarter_primary_page(ytd=True)),
        (VERSION_2, 2, _movement_note([current, comparative])),
    ]


def test_partial_period_lane_maps_current_and_types_only_exact_comparative_cells() -> None:
    indexed, trials, pages = _run_pages(_partial_period_lane_fixture())

    assert trials[0]["status"] == READY
    mapped = _mapped(trials[0])
    for role in ("CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"):
        assert mapped[role]["values"][0]["coefficient"] is not None
        assert mapped[role]["values"][1] == {
            "coefficient": None,
            "source_text": None,
            "state": "UNOBSERVED_SOURCE_LANE",
        }
    authority = indexed["candidate_dispositions"][0]["cluster"][
        "credit_risk_provision_expense_query_adapter_receipt"
    ]["source_authority_receipt"]
    assert len(authority["accepted_source_cell_axis"]) == 3
    assert len(authority["rejected_source_cell_axis"]) == 3
    assert {
        item["semantic_lane"] for item in authority["rejected_source_cell_axis"]
    } == {"COMPARATIVE_PERIOD"}
    coverage = build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
        indexed_query_evidence=indexed,
        trials=trials,
        page_json_by_document=pages,
        compiled_specs=_compiled(),
    )
    rejected_entries = [
        item
        for item in coverage["movement_cell_axis"]
        if item["evidence"]["semantic_lane"] == "COMPARATIVE_PERIOD"
    ]
    assert rejected_entries
    assert all(
        item["evidence"]["source_authority_disposition"]
        == "EXACT_REJECTED_SOURCE_ONLY_CELL"
        for item in rejected_entries
    )


def test_rejected_comparative_cell_never_whitelists_unmapped_current_neighbor() -> None:
    indexed, trials, pages = _run_pages(_partial_period_lane_fixture())
    stripped = canonical_clone_v1(trials)
    stripped[0]["mappings"] = [
        item
        for item in stripped[0]["mappings"]
        if item["role"] != "CUSTOMER_GENERAL"
    ]

    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="nested movement coverage is invalid",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=stripped,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_mapping_cannot_redirect_to_exact_rejected_source_cell() -> None:
    indexed, trials, pages = _run_pages(_partial_period_lane_fixture())
    redirected = canonical_clone_v1(trials)
    general = next(
        item
        for item in redirected[0]["mappings"]
        if item["role"] == "CUSTOMER_GENERAL"
    )
    assert len(general["source_refs"]) == 1
    general["source_refs"][0]["locator"]["table_id"] = "t2"

    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="nested movement coverage is invalid",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=redirected,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_two_column_derived_parent_never_masks_unmapped_child_role() -> None:
    current = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80"])],
        title="Kỳ này từ 01/01/2026 đến 30/06/2026",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước từ 01/01/2025 đến 30/06/2025",
    )
    for table in (current, comparative):
        table["columns"] = table["columns"][:2]
    indexed, trials, pages = _run_pages(
        [(VERSION_1, 1, _movement_note([current, comparative]))]
    )
    assert trials[0]["status"] == READY
    assert set(_mapped(trials[0])) == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
    }

    stripped = canonical_clone_v1(trials)
    stripped[0]["mappings"] = [
        item
        for item in stripped[0]["mappings"]
        if item["role"] != "CUSTOMER_GENERAL"
    ]
    with pytest.raises(
        GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
        match="nested movement coverage is invalid",
    ):
        build_credit_risk_provision_expense_source_row_coverage_receipt_v1(
            indexed_query_evidence=indexed,
            trials=stripped,
            page_json_by_document=pages,
            compiled_specs=_compiled(),
        )


def test_relative_detail_cannot_inherit_bare_primary_period_labels() -> None:
    movement = _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Kỳ này năm 2026",
            ),
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước năm 2025",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, _primary_page("(100)", "(80)")), (VERSION_2, 2, movement)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_DETAIL_PRIMARY_DURATION_SCOPE_CONFLICT" in trials[0]["reasons"]


def test_relative_detail_inherits_exact_lane_specific_primary_ranges() -> None:
    primary = _primary_page("(100)", "(80)")
    columns = primary["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"] = [
        "Kỳ này từ 01/01/2026 đến 30/06/2026",
        "Triệu đồng",
    ]
    columns[1]["header_path_exact"] = [
        "Kỳ trước từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
    ]
    movement = _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Kỳ này năm 2026",
            ),
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước năm 2025",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, movement)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["FAMILY_ROOT_TOTAL"]["values"]
    ] == [-100, -80]


def test_relative_detail_visible_year_conflict_with_exact_parent_is_unresolved() -> None:
    primary = _primary_page("(100)", "(80)")
    columns = primary["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"] = [
        "Kỳ này từ 01/01/2026 đến 30/06/2026",
        "Triệu đồng",
    ]
    columns[1]["header_path_exact"] = [
        "Kỳ trước từ 01/01/2025 đến 30/06/2025",
        "Triệu đồng",
    ]
    movement = _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Kỳ này năm 2024",
            ),
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước năm 2023",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, movement)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_DETAIL_PRIMARY_DURATION_SCOPE_CONFLICT" in trials[0]["reasons"]


def test_invalid_calendar_date_is_explicit_and_fails_closed() -> None:
    primary = _primary_page("(100)", "(80)")
    columns = primary["sections"][0]["tables"][0]["columns"]
    columns[0]["header_path_exact"] = [
        "Kỳ này từ 01/01/2026 đến 31/02/2026",
        "Triệu đồng",
    ]
    columns[1]["header_path_exact"] = [
        "Kỳ trước từ 01/01/2025 đến 31/02/2025",
        "Triệu đồng",
    ]
    movement = _movement_note(
        [
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
                title="Kỳ này",
            ),
            _movement_table(
                [_row("Trích lập dự phòng trong kỳ", ["15", "65", "80"])],
                title="Kỳ trước",
            ),
        ]
    )
    indexed, trials, _pages = _run_pages(
        [(VERSION_1, 1, primary), (VERSION_2, 2, movement)]
    )

    assert indexed["candidate_dispositions"][0]["disposition"] == UNRESOLVED
    assert trials[0]["status"] == UNRESOLVED
    assert trials[0]["mappings"] == []
    assert "F37_DETAIL_PRIMARY_DURATION_SCOPE_CONFLICT" in trials[0]["reasons"]
    authority = indexed["candidate_dispositions"][0]["cluster"][
        "credit_risk_provision_expense_query_adapter_receipt"
    ]["source_authority_receipt"]
    invalid_axis = authority["period_authority_axis"]
    assert len(invalid_axis) == 2
    assert {item["root_scope"]["basis"] for item in invalid_axis} == {
        "INVALID_DATE"
    }
    assert {
        reason
        for item in invalid_axis
        for reason in item["root_scope"]["reasons"]
    } == {"INVALID_CALENDAR_DATE"}
    assert {item["compatibility"] for item in invalid_axis} == {
        "PRIMARY_PARENT_INVALID_CALENDAR_DATE"
    }


def test_later_conflicting_explicit_range_cannot_hide_behind_first_pair() -> None:
    detail = _family37_period_scope_v1(
        "Từ 01/01/2026 đến 30/06/2026; "
        "kỳ báo cáo từ 01/01/2026 đến 31/03/2026",
        semantic_role="CURRENT_PERIOD",
    )
    root = _family37_period_scope_v1(
        "Từ 01/01/2026 đến 30/06/2026",
        semantic_role="CURRENT_PERIOD",
    )

    allowed, _reason = _family37_period_compatibility_v1(detail, root)

    assert not allowed
    assert detail["basis"] == "INVALID_RANGE"
    assert detail["reasons"] == ["CONFLICTING_EXPLICIT_DATE_RANGES"]


def test_relative_word_cannot_erase_invalid_explicit_written_date() -> None:
    detail = _family37_period_scope_v1(
        "Trích lập dự phòng trong kỳ kết thúc ngày 31 tháng 02 năm 2026",
        semantic_role="CURRENT_PERIOD",
    )
    root = _family37_period_scope_v1(
        "Từ 01/01/2026 đến 30/06/2026",
        semantic_role="CURRENT_PERIOD",
    )

    allowed, _reason = _family37_period_compatibility_v1(detail, root)

    assert not allowed
    assert detail["basis"] == "INVALID_DATE"
    assert detail["reasons"] == ["INVALID_CALENDAR_DATE"]
