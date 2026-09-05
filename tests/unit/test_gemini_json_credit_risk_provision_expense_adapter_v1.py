from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation.gemini_json_credit_risk_provision_expense_family_v1 import (
    GeminiJsonCreditRiskProvisionExpenseFamilyV1Error,
    _apply_document_repairs,
    build_credit_risk_provision_expense_source_row_coverage_receipt_v1,
    build_gemini_json_credit_risk_provision_expense_indexed_query_evidence_v1,
    build_gemini_json_credit_risk_provision_expense_trials_v1,
    compile_gemini_json_credit_risk_provision_expense_family_specs_v1,
    validate_gemini_json_credit_risk_provision_expense_replay_v1,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_indexed_multitable_hierarchical_query_evidence_v1,
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
    page_json_by_document = {1: by_version}
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


def test_unitless_shared_duration_header_is_bound_by_exact_primary_root() -> None:
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
    assert {mapping["unit"] for mapping in trials[0]["mappings"]} == {"MILLION_VND"}
    receipt = trials[0]["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]
    assert len(receipt["unit_corroboration_receipts"]) == 1
    assert len(receipt["structural_projection_receipts"]) == 1


def test_current_only_transposed_movement_preserves_null_comparative_lanes() -> None:
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
    assert trial["status"] == READY
    for role in ("CUSTOMER_PROVISION", "CUSTOMER_GENERAL", "CUSTOMER_SPECIFIC"):
        assert _mapped(trial)[role]["values"][1] == {
            "coefficient": None,
            "source_text": None,
            "state": "UNOBSERVED_SOURCE_LANE",
        }
    assert [cell["coefficient"] for cell in _mapped(trial)["FAMILY_ROOT_TOTAL"]["values"]] == [
        -103,
        -82,
    ]


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


def test_single_explicit_comparative_movement_preserves_comparative_lane() -> None:
    table = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["20", "80", "100"])],
        title="Kỳ trước",
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
    receipt = trial["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["transposed_receipt"]
    assert receipt["current"] is None
    assert receipt["rule"] == (
        "ONE_SOURCE_VISIBLE_COMPARATIVE_DURATION_MOVEMENT_"
        "OBSERVATION_CURRENT_UNOBSERVED"
    )


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
    assert trials[0]["reasons"] == [
        "SOURCE_VISIBLE_TRANSPOSED_CUSTOMER_EXPENSE_DURATION_OR_"
        "GROSS_NET_PRESENTATION_AMBIGUOUS"
    ]


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
    assert trials[0]["candidate_count"] == 1


def test_two_role_movement_derives_customer_total_and_ignores_utilization() -> None:
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
    assert all(
        source_ref["money_column_ordinals"] == [1, 2]
        for source_ref in mapped["CUSTOMER_PROVISION"]["source_refs"]
    )


def test_customer_summary_title_owns_adjacent_current_and_annual_movements() -> None:
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
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _customer_balance_page("(1.000)", "(800)")),
            (VERSION_2, 2, _primary_page("(100)", "(70)")),
            ("gfpstorev1:json:" + "e" * 64, 3, note),
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
        "CURRENT_DURATION_MOVEMENT_ONLY_NONCOMPARABLE_ANNUAL_"
        "ROLLFORWARD_IS_SOURCE_ONLY"
    )
    assert {
        row["disposition"] for row in transposed["source_only_rows"]
    } == {"NONCOMPARABLE_ANNUAL_ROLLFORWARD_NOT_COMPARATIVE_DURATION"}


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
        title="Kỳ này",
    )
    comparative = _movement_table(
        [_row("Trích lập/(hoàn nhập) dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước",
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
        title="Kỳ này",
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", "65"])],
        title="Kỳ trước",
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
        [_row("Trích lập dự phòng trong kỳ", ["20", None])], title="Kỳ này"
    )
    comparative = _movement_table(
        [_row("Trích lập dự phòng trong kỳ", ["15", None])], title="Kỳ trước"
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


def test_explicit_year_pairs_with_explicit_comparative_marker() -> None:
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
    assert trials[0]["status"] == READY
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["CUSTOMER_PROVISION"]["values"]
    ] == [100, 80]


def test_unitless_movement_chooses_unique_matching_balance_representation() -> None:
    vnd_balance = _customer_balance_page(
        "(100.000.000)", "(80.000.000)", unit="VND"
    )
    million_balance = _customer_balance_page("(100)", "(80)")
    vnd_root = _primary_page("(30.000.000)", "(20.000.000)")
    vnd_root["sections"][0]["tables"][0]["unit_exact"] = "VND"
    for column in vnd_root["sections"][0]["tables"][0]["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0], "VND"]
    movement = _movement_table(
        [
            _row("Trích lập dự phòng trong kỳ", ["10", "20"]),
            _row("Số dư cuối kỳ", ["60", "40"], kind="TOTAL"),
        ],
        title="Kỳ này",
        unit=None,
    )
    movement["columns"] = movement["columns"][:2]
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, vnd_balance),
            (VERSION_2, 2, million_balance),
            ("gfpstorev1:json:" + "e" * 64, 3, vnd_root),
            (
                "gfpstorev1:json:" + "f" * 64,
                4,
                _primary_page("(30)", "(20)"),
            ),
            (
                "gfpstorev1:json:" + "1" * 64,
                5,
                _movement_note([movement]),
            ),
        ]
    )
    assert trials[0]["status"] == READY
    assert {mapping["unit"] for mapping in trials[0]["mappings"]} == {
        "MILLION_VND"
    }
    assert [
        cell["coefficient"]
        for cell in _mapped(trials[0])["FAMILY_ROOT_TOTAL"]["values"]
    ] == [-30, -20]


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


def test_adjacent_customer_continuation_carries_only_visible_role_scope() -> None:
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
    _indexed, trials, pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(100)", "(80)")),
            (VERSION_2, 2, first),
            ("gfpstorev1:json:" + "f" * 64, 3, second),
        ]
    )
    assert same_typed_json_v1(second, original_second)
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


def test_separate_provision_and_reversal_select_exact_net_annual_presentation() -> None:
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
    _indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(90)", "(75)")),
            (VERSION_2, 2, _movement_note([_movement_table(rows)])),
        ]
    )
    mapped = _mapped(trials[0])
    assert [cell["coefficient"] for cell in mapped["CUSTOMER_PROVISION"]["values"]] == [
        90,
        75,
    ]
    assert len(mapped["CUSTOMER_PROVISION"]["source_refs"]) == 4


def test_separate_reversal_is_source_only_when_primary_presentation_is_gross() -> None:
    def table(year: int, gross: list[str], reversal: list[str]) -> dict[str, Any]:
        return _movement_table(
            [
                _row("Dự phòng rủi ro trích lập trong kỳ", gross),
                _row("Số hoàn nhập dự phòng trong kỳ", reversal),
            ],
            title=f"Thay đổi dự phòng năm {year}",
        )

    _indexed, trials, _pages = _run_pages(
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
    candidate = trials[0]["candidates"][0]
    mapped = _mapped(trials[0])
    assert [cell["coefficient"] for cell in mapped["CUSTOMER_PROVISION"]["values"]] == [
        100,
        80,
    ]
    assert len(mapped["CUSTOMER_PROVISION"]["source_refs"]) == 2
    assert len(candidate["closure_receipt"]["source_only_unmapped_rows"]) == 2
    coverage = candidate["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["source_role_coverage"]
    assert coverage["mapped_observation_count"] == 6
    assert coverage["source_only_observation_count"] == 6
    assert coverage["violation_count"] == 0


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
                title="Năm 2025",
            ),
            _movement_table(
                [_row("Dự phòng rủi ro trích lập trong kỳ", ["15", "65", "80"])],
                title="Năm 2024",
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


def test_noncomparable_prior_annual_rollforward_does_not_fill_duration_lane() -> None:
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
    mapped = _mapped(trials[0])["CUSTOMER_PROVISION"]
    assert [cell["coefficient"] for cell in mapped["values"]] == [100, None]
    assert mapped["values"][1]["state"] == "UNOBSERVED_SOURCE_LANE"
    source_only = trials[0]["candidates"][0]["closure_receipt"][
        "source_only_unmapped_rows"
    ]
    assert {item["row_ordinal"] for item in source_only} == {1, 2}


def test_transposed_local_unit_without_primary_root_maps_only_observed_roles() -> None:
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
    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] == READY
    assert set(_mapped(trials[0])) == {
        "CUSTOMER_GENERAL",
        "CUSTOMER_PROVISION",
        "CUSTOMER_SPECIFIC",
    }


def test_transposed_unitless_without_primary_root_fails_closed() -> None:
    note = _movement_note(
        [
            _movement_table(
                [_row("Trích lập trong kỳ", ["20", "80", "100"])],
                unit=None,
            )
        ]
    )
    indexed, trials, _pages = _run_pages([(VERSION_1, 1, note)])
    assert indexed["candidate_dispositions"][0]["disposition"] == NOT_OBSERVED
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

    indexed, trials, _pages = _run_pages(
        [
            (VERSION_1, 1, _primary_page("(103)", "(83)")),
            (VERSION_2, 2, _movement_note([table(2025), table(2024)])),
        ]
    )
    assert indexed["candidate_dispositions"][0]["disposition"] == READY
    assert trials[0]["status"] != NOT_OBSERVED
    assert trials[0]["mappings"] == []
    assert trials[0]["reasons"] == [
        "SOURCE_VISIBLE_TRANSPOSED_CUSTOMER_EXPENSE_DURATION_OR_"
        "GROSS_NET_PRESENTATION_AMBIGUOUS"
    ]
    coverage = trials[0]["candidates"][0]["closure_receipt"][
        "credit_risk_provision_expense_adapter_receipt"
    ]["source_role_coverage"]
    assert coverage["covered_observation_count"] == 12
    assert coverage["violation_count"] == 0


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
