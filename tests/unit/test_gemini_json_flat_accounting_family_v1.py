from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
    validate_gemini_json_flat_family_sweep_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _specs() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-cash-precious-metals-topology-v1.json",
            "config/families/tm-cash-precious-metals-evaluation-v1.json",
            "config/families/tm-cash-precious-metals-schema-binding-v1.json",
        )
    )


def _hierarchical_specs() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-central-bank-deposits-topology-v2.json",
            "config/families/tm-central-bank-deposits-evaluation-v1.json",
            "config/families/tm-central-bank-deposits-schema-binding-v2.json",
        )
    )


def _recursive_specs() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-interbank-deposits-loans-topology-v4.json",
            "config/families/tm-interbank-deposits-loans-evaluation-v4.json",
            "config/families/tm-interbank-deposits-loans-schema-binding-v4.json",
        )
    )


def _loan_type_specs() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-loan-type-classification-topology-v1.json",
            "config/families/tm-loan-type-classification-evaluation-v1.json",
            "config/families/tm-loan-type-classification-schema-binding-v1.json",
        )
    )


def _loan_type_page(*, percentage_companions: bool) -> dict:
    columns = [
        {"header_path_exact": ["31.12.2025", "Triệu đồng"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2024", "Triệu đồng"], "value_kind": "MONEY"},
    ]
    values = [
        ["100", "90"],
        ["20", "10"],
        ["120", "100"],
    ]
    if percentage_companions:
        columns = [
            {"header_path_exact": ["Số cuối năm", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số cuối năm", "%"], "value_kind": "PERCENT"},
            {"header_path_exact": ["Số đầu năm", "Triệu đồng"], "value_kind": "MONEY"},
            {"header_path_exact": ["Số đầu năm", "%"], "value_kind": "PERCENT"},
        ]
        values = [
            ["100", "83,33", "90", "90,00"],
            ["20", "16,67", "10", "10,00"],
            ["120", "100,00", "100", "100,00"],
        ]
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
                        "columns": columns,
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": [
                                    "Cho vay khách hàng",
                                    "Cho vay các tổ chức kinh tế, cá nhân trong nước",
                                ],
                                "label_exact": "Cho vay các tổ chức kinh tế, cá nhân trong nước",
                                "row_kind": "ITEM",
                                "values_exact": values[0],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Cho vay khách hàng",
                                    "Cho vay khác",
                                ],
                                "label_exact": "Cho vay khác",
                                "row_kind": "ITEM",
                                "values_exact": values[1],
                            },
                            {
                                "hierarchy_path_exact": ["Cho vay khách hàng", None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": values[2],
                            },
                        ],
                        "title_exact": "Theo loại hình cho vay",
                        "unit_exact": "Triệu đồng",
                    }
                ],
            }
        ],
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
    }


def _evaluate_loan_type(page: dict) -> dict:
    topology, evaluation, schema = _loan_type_specs()
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "6" * 64,
        physical_page=11,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _trading_specs() -> tuple[dict, dict, dict]:
    return tuple(
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-trading-securities-topology-v1.json",
            "config/families/tm-trading-securities-evaluation-v1.json",
            "config/families/tm-trading-securities-schema-binding-v1.json",
        )
    )


def _page() -> dict:
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "5. TIỀN MẶT, VÀNG BẠC, ĐÁ QUÝ",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31.12.2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31.12.2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Tiền mặt bằng VND"],
                                "label_exact": "Tiền mặt bằng VND",
                                "row_kind": "ITEM",
                                "values_exact": ["100", "90"],
                            },
                            {
                                "hierarchy_path_exact": ["Tiền mặt bằng ngoại tệ"],
                                "label_exact": "Tiền mặt bằng ngoại tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["20", "10"],
                            },
                            {
                                "hierarchy_path_exact": ["Vàng tiền tệ"],
                                "label_exact": "Vàng tiền tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["-", None],
                            },
                            {
                                "hierarchy_path_exact": [None],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": ["120", "100"],
                            },
                        ],
                        "title_exact": None,
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
    topology, evaluation, schema = _specs()
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "1" * 64,
        physical_page=7,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _trading_page(*, provision_only: bool = False) -> dict:
    rows = [
        {
            "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh"],
            "label_exact": "Dự phòng rủi ro chứng khoán kinh doanh",
            "row_kind": "SUBTOTAL",
            "values_exact": ["-", "-"],
        }
    ]
    if not provision_only:
        rows[:0] = [
            {
                "hierarchy_path_exact": ["Chứng khoán nợ"],
                "label_exact": "Chứng khoán nợ",
                "row_kind": "SUBTOTAL",
                "values_exact": ["100", "90"],
            },
            {
                "hierarchy_path_exact": ["Chứng khoán vốn"],
                "label_exact": "Chứng khoán vốn",
                "row_kind": "SUBTOTAL",
                "values_exact": ["50", "40"],
            },
        ]
    rows.append(
        {
            "hierarchy_path_exact": ["Giá trị thuần"],
            "label_exact": "Giá trị thuần",
            "row_kind": "TOTAL",
            "values_exact": ["0", "0"] if provision_only else ["150", "130"],
        }
    )
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "CHỨNG KHOÁN KINH DOANH",
                "tables": [
                    {
                        "columns": [
                            {"header_path_exact": ["2025"], "value_kind": "MONEY"},
                            {"header_path_exact": ["2024"], "value_kind": "MONEY"},
                        ],
                        "continuation": "NONE",
                        "rows": rows,
                        "title_exact": None,
                        "unit_exact": "Triệu đồng",
                    }
                ],
            }
        ],
        "completion": {"all_relevant_content_transcribed": True, "uncertainty_exact": []},
    }


def _evaluate_trading(page: dict) -> dict:
    topology, evaluation, schema = _trading_specs()
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "4" * 64,
        physical_page=8,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _lane_specific_trading_page() -> dict:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "SUBTOTAL",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán vốn"],
            "label_exact": "Chứng khoán vốn",
            "row_kind": "SUBTOTAL",
            "values_exact": ["50", "70"],
        },
        {
            "hierarchy_path_exact": [
                "Chứng khoán vốn",
                "Chứng khoán vốn do các TCTD trong nước phát hành",
            ],
            "label_exact": "Chứng khoán vốn do các TCTD trong nước phát hành",
            "row_kind": "ITEM",
            "values_exact": ["20", "30"],
        },
        {
            "hierarchy_path_exact": [
                "Chứng khoán vốn",
                "Chứng khoán vốn do các TCKT trong nước phát hành",
            ],
            "label_exact": "Chứng khoán vốn do các TCKT trong nước phát hành",
            "row_kind": "ITEM",
            "values_exact": ["30", "35"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán kinh doanh khác"],
            "label_exact": "Chứng khoán kinh doanh khác",
            "row_kind": "SUBTOTAL",
            "values_exact": ["5", "5"],
        },
        {
            "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh"],
            "label_exact": "Dự phòng rủi ro chứng khoán kinh doanh",
            "row_kind": "SUBTOTAL",
            "values_exact": ["(10)", "(10)"],
        },
        {
            "hierarchy_path_exact": ["Giá trị thuần"],
            "label_exact": "Giá trị thuần",
            "row_kind": "TOTAL",
            "values_exact": ["145", "150"],
        },
    ]
    return page


def _hierarchical_page() -> dict:
    page = _page()
    section = page["sections"][0]
    section["title_exact"] = "6. TIỀN GỬI TẠI NGÂN HÀNG NHÀ NƯỚC"
    table = section["tables"][0]
    table["rows"] = [
        {
            "hierarchy_path_exact": ["Tiền gửi tại Ngân hàng Nhà nước Việt Nam"],
            "label_exact": "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
            "row_kind": "SUBTOTAL",
            "values_exact": ["120", "100"],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                "Bằng VND",
            ],
            "label_exact": "Bằng VND",
            "row_kind": "ITEM",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi tại Ngân hàng Nhà nước Việt Nam",
                "Bằng ngoại tệ",
            ],
            "label_exact": "Bằng ngoại tệ",
            "row_kind": "ITEM",
            "values_exact": ["20", "10"],
        },
        {
            "hierarchy_path_exact": ["Tiền gửi tại Ngân hàng Trung ương Lào"],
            "label_exact": "Tiền gửi tại Ngân hàng Trung ương Lào",
            "row_kind": "SUBTOTAL",
            "values_exact": ["5", "4"],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi tại Ngân hàng Trung ương Lào",
                "Bằng VND",
            ],
            "label_exact": "Bằng VND",
            "row_kind": "ITEM",
            "values_exact": ["2", "1"],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi tại Ngân hàng Trung ương Lào",
                "Bằng ngoại tệ",
            ],
            "label_exact": "Bằng ngoại tệ",
            "row_kind": "ITEM",
            "values_exact": ["3", "3"],
        },
        {
            "hierarchy_path_exact": ["Tiền gửi tại Ngân hàng Quốc gia Campuchia"],
            "label_exact": "Tiền gửi tại Ngân hàng Quốc gia Campuchia",
            "row_kind": "ITEM",
            "values_exact": ["7", "6"],
        },
        {
            "hierarchy_path_exact": ["Tiền gửi phong tỏa"],
            "label_exact": "Tiền gửi phong tỏa",
            "row_kind": "ITEM",
            "values_exact": ["1", "2"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["133", "112"],
        },
    ]
    return page


def _evaluate_hierarchical(page: dict) -> dict:
    topology, evaluation, schema = _hierarchical_specs()
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "3" * 64,
        physical_page=11,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def _recursive_page() -> dict:
    return {
        "status": "FINANCIAL_NOTE_CONTENT",
        "sections": [
            {
                "content_kind": "FINANCIAL_NOTE",
                "narratives_exact": [],
                "statement_type": "NOT_APPLICABLE",
                "title_exact": "Tiền gửi và cho vay các TCTD khác",
                "tables": [
                    {
                        "columns": [
                            {
                                "header_path_exact": ["31.12.2025", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                            {
                                "header_path_exact": ["31.12.2024", "Triệu đồng"],
                                "value_kind": "MONEY",
                            },
                        ],
                        "continuation": "NONE",
                        "rows": [
                            {
                                "hierarchy_path_exact": ["Tiền gửi tại các TCTD khác"],
                                "label_exact": "Tiền gửi tại các TCTD khác",
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi tại các TCTD khác",
                                    "Tiền gửi không kỳ hạn",
                                ],
                                "label_exact": "Tiền gửi không kỳ hạn",
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi tại các TCTD khác",
                                    "Tiền gửi không kỳ hạn",
                                    "Bằng VND",
                                ],
                                "label_exact": "Bằng VND",
                                "row_kind": "ITEM",
                                "values_exact": ["60", "50"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi tại các TCTD khác",
                                    "Tiền gửi không kỳ hạn",
                                    "Bằng ngoại tệ",
                                ],
                                "label_exact": "Bằng ngoại tệ",
                                "row_kind": "ITEM",
                                "values_exact": ["40", "40"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi tại các TCTD khác",
                                    "Tiền gửi không kỳ hạn",
                                ],
                                "label_exact": None,
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["100", "90"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi tại các TCTD khác",
                                    "Tiền gửi có kỳ hạn",
                                ],
                                "label_exact": "Tiền gửi có kỳ hạn",
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["50", "40"],
                            },
                            {
                                "hierarchy_path_exact": ["Tiền gửi tại các TCTD khác"],
                                "label_exact": None,
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["150", "130"],
                            },
                            {
                                "hierarchy_path_exact": ["Cho vay các TCTD khác"],
                                "label_exact": "Cho vay các TCTD khác",
                                "row_kind": "GROUP",
                                "values_exact": [None, None],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Cho vay các TCTD khác",
                                    "Bằng VND",
                                ],
                                "label_exact": "Bằng VND",
                                "row_kind": "ITEM",
                                "values_exact": ["20", "10"],
                            },
                            {
                                "hierarchy_path_exact": ["Cho vay các TCTD khác"],
                                "label_exact": None,
                                "row_kind": "SUBTOTAL",
                                "values_exact": ["20", "10"],
                            },
                            {
                                "hierarchy_path_exact": [
                                    "Tiền gửi và cho vay các TCTD khác",
                                    "Dự phòng rủi ro",
                                ],
                                "label_exact": "Dự phòng rủi ro",
                                "row_kind": "ITEM",
                                "values_exact": ["-", "(1)"],
                            },
                            {
                                "hierarchy_path_exact": ["Tiền gửi và cho vay các TCTD khác"],
                                "label_exact": None,
                                "row_kind": "TOTAL",
                                "values_exact": ["170", "139"],
                            },
                        ],
                        "title_exact": None,
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


def _evaluate_recursive(page: dict) -> dict:
    topology, evaluation, schema = _recursive_specs()
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "4" * 64,
        physical_page=19,
        section_id="s1",
        table_id="t1",
        compiled_specs=compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema),
    )


def test_flat_family_closes_exact_dash_blank_and_reordered_direct_frontier() -> None:
    topology, evaluation, schema = _specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    assert len(compiled["anchor_alias_groups"]) == 1
    assert len(compiled["anchor_alias_groups"][0]) == 2

    result = _evaluate(_page())
    assert result["status"] == READY
    assert result["reasons"] == []
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        561,
        562,
        563,
        565,
    ]
    assert result["closure_receipt"]["lane_component_sums"] == [120, 100]
    assert result["mappings"][3]["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {
            "coefficient": 0,
            "source_text": None,
            "state": "BLANK_ZERO_IF_EQUATION_EXACT",
        },
    ]

    reordered = _page()
    reordered["sections"][0]["tables"][0]["rows"][:3] = list(
        reversed(reordered["sections"][0]["tables"][0]["rows"][:3])
    )
    replay = _evaluate(reordered)
    assert replay["status"] == READY
    assert replay["closure_receipt"]["component_roles_in_source_order"] == [
        "MONETARY_GOLD",
        "CASH_FOREIGN",
        "CASH_VND",
    ]


def test_flat_family_fails_closed_on_shift_duplicate_extra_parent_or_arithmetic() -> None:
    shifted = _page()
    shifted["sections"][0]["tables"][0]["rows"][0]["values_exact"] = ["100"]
    assert "ROW_VALUE_VECTOR_DOES_NOT_MATCH_COLUMN_AXIS" in _evaluate(shifted)["reasons"]

    duplicate = _page()
    duplicate["sections"][0]["tables"][0]["rows"].insert(
        1, deepcopy(duplicate["sections"][0]["tables"][0]["rows"][0])
    )
    assert any(
        reason.startswith("REQUIRED_ROLE_USE_COUNT_NOT_ONE:CASH_VND:2")
        for reason in _evaluate(duplicate)["reasons"]
    )

    extra = _page()
    extra["sections"][0]["tables"][0]["rows"].insert(
        2,
        {
            "hierarchy_path_exact": ["Không xác định"],
            "label_exact": "Không xác định",
            "row_kind": "ITEM",
            "values_exact": ["0", "0"],
        },
    )
    assert "UNBOUND_VISIBLE_NUMERIC_OR_SEMANTIC_ROWS" in _evaluate(extra)["reasons"]

    wrong_parent = _page()
    wrong_parent["sections"][0]["title_exact"] = "RỦI RO THANH KHOẢN"
    wrong = _evaluate(wrong_parent)
    assert "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_OR_TABLE_TITLE" in wrong["reasons"]
    assert "HARD_NEGATIVE_FAMILY_VISIBLE_IN_CANDIDATE" in wrong["reasons"]

    mismatch = _page()
    mismatch["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "121"
    assert "VISIBLE_TOTAL_NOT_EXACT_DIRECT_COMPONENT_SUM:0" in _evaluate(mismatch)["reasons"]


def test_hierarchical_family_uses_one_recursive_frontier_and_derived_aggregate() -> None:
    topology, evaluation, schema = _hierarchical_specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    assert compiled["component_group_by_role"] == {
        "DEPOSIT_FOREIGN_CURRENCY": "CENTRAL_BANK_VIETNAM_PARENT",
        "DEPOSIT_VND": "CENTRAL_BANK_VIETNAM_PARENT",
    }

    result = _evaluate_hierarchical(_hierarchical_page())
    assert result["status"] == READY
    assert result["reasons"] == []
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        569,
        571,
        572,
        570,
        573,
        574,
    ]
    aggregate = result["mappings"][-1]
    assert aggregate["derived_from_roles"] == [
        "CENTRAL_BANK_LAOS",
        "CENTRAL_BANK_CAMBODIA",
    ]
    assert aggregate["derived_from_row_ids"] == ["r4", "r7"]
    assert [cell["coefficient"] for cell in aggregate["values"]] == [12, 10]
    receipt = result["closure_receipt"]
    assert receipt["component_roles_in_source_order"] == [
        "CENTRAL_BANK_VIETNAM_PARENT",
        "CENTRAL_BANK_LAOS",
        "CENTRAL_BANK_CAMBODIA",
        "BLOCKED_DEPOSIT",
    ]
    assert receipt["lane_component_sums"] == [133, 112]
    assert [equation["result_role"] for equation in receipt["nested_equations"]] == [
        "CENTRAL_BANK_VIETNAM_PARENT",
        "CENTRAL_BANK_LAOS",
    ]

    reordered = _hierarchical_page()
    rows = reordered["sections"][0]["tables"][0]["rows"]
    rows[3:8] = [rows[6], rows[7], rows[3], rows[4], rows[5]]
    replay = _evaluate_hierarchical(reordered)
    assert replay["status"] == READY
    assert replay["closure_receipt"]["lane_component_sums"] == [133, 112]


def test_hierarchical_family_rejects_partial_mixed_duplicate_extra_and_mismatch() -> None:
    partial = _hierarchical_page()
    partial["sections"][0]["tables"][0]["rows"].pop(2)
    assert any(
        reason.startswith("SOURCE_GROUP_COMPONENT_FRONTIER_IS_PARTIAL")
        for reason in _evaluate_hierarchical(partial)["reasons"]
    )

    local_mismatch = _hierarchical_page()
    local_mismatch["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "121"
    assert (
        "NESTED_PARENT_NOT_EXACT_CHILD_SUM:CENTRAL_BANK_VIETNAM_PARENT"
        in (_evaluate_hierarchical(local_mismatch)["reasons"])
    )

    duplicate = _hierarchical_page()
    duplicate["sections"][0]["tables"][0]["rows"].insert(
        7, deepcopy(duplicate["sections"][0]["tables"][0]["rows"][6])
    )
    assert any(
        reason.startswith("OPTIONAL_ROLE_USE_COUNT_ABOVE_ONE:CENTRAL_BANK_CAMBODIA")
        for reason in _evaluate_hierarchical(duplicate)["reasons"]
    )

    extra = _hierarchical_page()
    extra["sections"][0]["tables"][0]["rows"].insert(
        -1,
        {
            "hierarchy_path_exact": ["Ngoài frontier"],
            "label_exact": "Ngoài frontier",
            "row_kind": "ITEM",
            "values_exact": ["0", "0"],
        },
    )
    assert "UNBOUND_VISIBLE_NUMERIC_OR_SEMANTIC_ROWS" in _evaluate_hierarchical(extra)["reasons"]

    root_mismatch = _hierarchical_page()
    root_mismatch["sections"][0]["tables"][0]["rows"][-1]["values_exact"][1] = "113"
    assert (
        "VISIBLE_TOTAL_NOT_EXACT_RECURSIVE_COMPONENT_SUM:1"
        in (_evaluate_hierarchical(root_mismatch)["reasons"])
    )


def test_hierarchical_specs_reject_invalid_equivalence_and_aggregate_frontiers() -> None:
    topology, evaluation, schema = _hierarchical_specs()
    invalid_evaluation = deepcopy(evaluation)
    invalid_evaluation["source_group_equivalences"][0]["group_role"] = "CENTRAL_BANK_LAOS"
    with pytest.raises(ValueError, match="source-group equivalence"):
        compile_gemini_json_flat_family_specs_v1(topology, invalid_evaluation, schema)

    invalid_schema = deepcopy(schema)
    invalid_schema["aggregate_role_bindings"][0]["source_roles"].append("DEPOSIT_VND")
    with pytest.raises(ValueError, match="aggregate role binding"):
        compile_gemini_json_flat_family_specs_v1(topology, evaluation, invalid_schema)


@pytest.mark.parametrize("percentage_companions", [False, True])
def test_period_value_hierarchy_maps_two_period_money_and_optional_percent_companions(
    percentage_companions: bool,
) -> None:
    result = _evaluate_loan_type(_loan_type_page(percentage_companions=percentage_companions))
    assert result["status"] == READY
    assert result["reasons"] == []
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [717, 718, 726]
    mappings = {mapping["role"]: mapping for mapping in result["mappings"]}
    assert [value["coefficient"] for value in mappings["LOAN_TYPE_CLASSIFICATION"]["values"]] == [
        120,
        100,
    ]
    assert mappings["OTHER_LOANS_AGGREGATE"]["derived_from_roles"] == [
        "OTHER_LOANS_EXPLICIT_COMPONENT"
    ]
    axis = result["closure_receipt"]["period_value_column_axis"]
    assert axis["money_column_indices"] == ([0, 2] if percentage_companions else [0, 1])
    assert axis["percent_column_indices"] == ([1, 3] if percentage_companions else [])
    if percentage_companions:
        assert mappings["DOMESTIC_ORGANIZATIONS_INDIVIDUALS"]["percentage_companion_values"] == [
            {
                "coefficient": 8333,
                "column_index": 1,
                "scale": 2,
                "source_text": "83,33",
                "state": "RAW_UNSIGNED_DECIMAL_PERCENT",
            },
            {
                "coefficient": 9000,
                "column_index": 3,
                "scale": 2,
                "source_text": "90,00",
                "state": "RAW_UNSIGNED_DECIMAL_PERCENT",
            },
        ]


def test_period_value_hierarchy_rejects_column_shift_bad_period_percent_and_money_sum() -> None:
    shifted = _loan_type_page(percentage_companions=True)
    columns = shifted["sections"][0]["tables"][0]["columns"]
    columns[1], columns[2] = columns[2], columns[1]
    assert (
        "PERIOD_VALUE_COLUMN_KIND_SEQUENCE_IS_NOT_DECLARED"
        in _evaluate_loan_type(shifted)["reasons"]
    )

    wrong_period = _loan_type_page(percentage_companions=True)
    wrong_period["sections"][0]["tables"][0]["columns"][3]["header_path_exact"][0] = "Số cuối năm"
    assert (
        "PERCENTAGE_COMPANION_PERIODS_DO_NOT_MATCH_MONEY_PERIODS"
        in _evaluate_loan_type(wrong_period)["reasons"]
    )

    bad_percent = _loan_type_page(percentage_companions=True)
    bad_percent["sections"][0]["tables"][0]["rows"][0]["values_exact"][1] = "8x,33"
    assert "ROW_PERCENT_CELL_IS_NOT_EXACT_DECIMAL:1" in _evaluate_loan_type(bad_percent)["reasons"]

    mismatch = _loan_type_page(percentage_companions=True)
    mismatch["sections"][0]["tables"][0]["rows"][-1]["values_exact"][0] = "121"
    assert any(
        reason.startswith("EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE")
        for reason in _evaluate_loan_type(mismatch)["reasons"]
    )


def test_period_value_hierarchy_accepts_reordered_optional_rows_but_rejects_duplicates_and_extra() -> (
    None
):
    reordered = _loan_type_page(percentage_companions=False)
    rows = reordered["sections"][0]["tables"][0]["rows"]
    rows[:2] = reversed(rows[:2])
    assert _evaluate_loan_type(reordered)["status"] == READY

    duplicate = _loan_type_page(percentage_companions=False)
    duplicate["sections"][0]["tables"][0]["rows"].insert(
        1, deepcopy(duplicate["sections"][0]["tables"][0]["rows"][0])
    )
    assert any(
        reason.startswith("ROLE_OCCURRENCE_COUNT_ABOVE_ONE")
        for reason in _evaluate_loan_type(duplicate)["reasons"]
    )

    extra = _loan_type_page(percentage_companions=False)
    extra["sections"][0]["tables"][0]["rows"].insert(
        -1,
        {
            "hierarchy_path_exact": ["Cho vay khách hàng", "Không khai báo"],
            "label_exact": "Không khai báo",
            "row_kind": "ITEM",
            "values_exact": ["1", "1"],
        },
    )
    assert "UNBOUND_VISIBLE_NUMERIC_ROWS:3" in _evaluate_loan_type(extra)["reasons"]


def test_recursive_family_closes_multilevel_subtotals_and_infers_provision_once() -> None:
    result = _evaluate_recursive(_recursive_page())
    assert result["status"] == READY
    assert result["reasons"] == []
    mappings = {mapping["role"]: mapping for mapping in result["mappings"]}
    assert [cell["coefficient"] for cell in mappings["INTERBANK_DEPOSITS_AND_LOANS"]["values"]] == [
        170,
        139,
    ]
    assert mappings["TOTAL_INTERBANK_PROVISION"]["inferred_from_role"] == (
        "INTERBANK_PROVISION_AMBIGUOUS"
    )
    assert mappings["TOTAL_INTERBANK_PROVISION"]["values"] == [
        {"coefficient": 0, "source_text": "-", "state": "DASH_ZERO"},
        {"coefficient": -1, "source_text": "(1)", "state": "RAW_SIGNED_INTEGER"},
    ]
    assert mappings["DEMAND_DEPOSIT_GROUP"]["row_id"] == "r5"
    assert mappings["INTERBANK_DEPOSIT_GROUP"]["row_id"] == "r7"
    assert mappings["INTERBANK_LOAN_GROUP"]["row_id"] == "r10"

    receipt = result["closure_receipt"]
    assert receipt["inferred_ambiguous_provision_role"] == "TOTAL_INTERBANK_PROVISION"
    root_equation = next(
        equation
        for equation in receipt["equations"]
        if equation["result_role"] == "INTERBANK_DEPOSITS_AND_LOANS"
    )
    assert root_equation["component_roles"] == [
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    ]
    assert root_equation["component_row_ids"] == ["r7", "r10", "r11"]
    assert root_equation["lane_component_sums"] == [170, 139]
    assert set(receipt["used_anonymous_result_row_ids"]) == {"r5", "r7", "r10", "r12"}
    assert all(
        mapping["row_id"] != "r3"
        for mapping in result["mappings"]
        if mapping["role"] == "INTERBANK_DEPOSIT_GROUP"
    )


def test_recursive_family_accepts_primary_statement_money_columns_without_geometry() -> None:
    page = _recursive_page()
    section = page["sections"][0]
    section["content_kind"] = "PRIMARY_FINANCIAL_STATEMENT"
    section["statement_type"] = "BALANCE_SHEET"
    table = section["tables"][0]
    table["unit_exact"] = None
    table["columns"] = [
        {"header_path_exact": ["Mã số"], "value_kind": "TEXT"},
        {"header_path_exact": ["31.12.2025", "Triệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["31.12.2024", "Triệu VND"], "value_kind": "MONEY"},
        {"header_path_exact": ["Thuyết minh"], "value_kind": "TEXT"},
    ]
    table["rows"] = [
        {
            "hierarchy_path_exact": ["Tiền gửi và cho vay các TCTD khác"],
            "label_exact": "Tiền gửi và cho vay các TCTD khác",
            "row_kind": "TOTAL",
            "values_exact": ["12", "170", "139", "6"],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi và cho vay các TCTD khác",
                "Tiền gửi tại các TCTD khác",
            ],
            "label_exact": "Tiền gửi tại các TCTD khác",
            "row_kind": "SUBTOTAL",
            "values_exact": [None, "150", "130", None],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi và cho vay các TCTD khác",
                "Cho vay các TCTD khác",
            ],
            "label_exact": "Cho vay các TCTD khác",
            "row_kind": "SUBTOTAL",
            "values_exact": [None, "20", "10", None],
        },
        {
            "hierarchy_path_exact": [
                "Tiền gửi và cho vay các TCTD khác",
                "Dự phòng rủi ro",
            ],
            "label_exact": "Dự phòng rủi ro",
            "row_kind": "ITEM",
            "values_exact": [None, "-", "(1)", None],
        },
    ]
    result = _evaluate_recursive(page)
    assert result["status"] == READY
    assert [mapping["role"] for mapping in result["mappings"]] == [
        "INTERBANK_DEPOSITS_AND_LOANS",
        "INTERBANK_DEPOSIT_GROUP",
        "INTERBANK_LOAN_GROUP",
        "TOTAL_INTERBANK_PROVISION",
    ]
    assert all(len(mapping["columns"]) == 2 for mapping in result["mappings"])


def test_recursive_family_rejects_wrong_arithmetic_scope_unit_duplicate_and_extra() -> None:
    wrong_root = _recursive_page()
    wrong_root["sections"][0]["tables"][0]["rows"][-1]["values_exact"][1] = "140"
    assert "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0" in _evaluate_recursive(wrong_root)["reasons"]

    wrong_scope = _recursive_page()
    provision = wrong_scope["sections"][0]["tables"][0]["rows"][-2]
    provision["hierarchy_path_exact"] = ["Cho vay các TCTD khác", "Dự phòng rủi ro"]
    assert "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0" in _evaluate_recursive(wrong_scope)["reasons"]

    missing_unit = _recursive_page()
    table = missing_unit["sections"][0]["tables"][0]
    table["unit_exact"] = None
    for column in table["columns"]:
        column["header_path_exact"] = [column["header_path_exact"][0]]
    assert (
        "PERIOD_UNIT_OR_MONEY_COLUMN_AXIS_IS_NOT_EXACT"
        in _evaluate_recursive(missing_unit)["reasons"]
    )

    duplicate = _recursive_page()
    duplicate["sections"][0]["tables"][0]["rows"].insert(
        4, deepcopy(duplicate["sections"][0]["tables"][0]["rows"][2])
    )
    assert any(
        reason.startswith("ROLE_OCCURRENCE_COUNT_ABOVE_ONE:DEMAND_DEPOSIT_VND:2")
        for reason in _evaluate_recursive(duplicate)["reasons"]
    )

    extra = _recursive_page()
    extra["sections"][0]["tables"][0]["rows"].insert(
        -1,
        {
            "hierarchy_path_exact": ["Tiền gửi và cho vay các TCTD khác", "Ngoài frontier"],
            "label_exact": "Ngoài frontier",
            "row_kind": "ITEM",
            "values_exact": ["1", "1"],
        },
    )
    assert "UNBOUND_VISIBLE_NUMERIC_ROWS:12" in _evaluate_recursive(extra)["reasons"]


def test_recursive_specs_and_sweep_fail_closed_under_coherent_tamper() -> None:
    topology, evaluation, schema = _recursive_specs()
    invalid = deepcopy(evaluation)
    invalid["hierarchical_closure_spec"]["equations"][0]["component_role_alternatives"][0][
        "component_roles"
    ].append("INTERBANK_DEPOSITS_AND_LOANS")
    with pytest.raises(ValueError, match="cyclic"):
        compile_gemini_json_flat_family_specs_v1(topology, invalid, schema)

    ready = _evaluate_recursive(_recursive_page())
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "5" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=[{"document_ordinal": 1, **ready}],
    )
    assert sweep["format_version"] == "GEMINI_JSON_HIERARCHICAL_ACCOUNTING_FAMILY_SWEEP_V3"
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep
    tampered = deepcopy(sweep)
    tampered["trials"][0]["closure_receipt"]["equations"][-1]["component_roles"].reverse()
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_gemini_json_flat_family_sweep_v1(tampered)


def test_flat_family_sweep_metrics_and_self_identity() -> None:
    topology, evaluation, schema = _specs()
    ready = _evaluate(_page())
    trials = [
        {
            "document_ordinal": 1,
            "mappings": ready["mappings"],
            "status": READY,
        },
        {"document_ordinal": 2, "mappings": [], "status": NOT_OBSERVED},
        {"document_ordinal": 3, "mappings": [], "status": UNRESOLVED},
    ]
    sweep = build_gemini_json_flat_family_sweep_v1(
        corpus_manifest_index_id="gjfccmiv1:index:" + "2" * 64,
        topology_spec=topology,
        evaluation_spec=evaluation,
        schema_binding_spec=schema,
        trials=trials,
    )
    assert sweep["metrics"] == {
        "document_count": 3,
        "mapping_count": 4,
        "not_observed_count": 1,
        "ready_count": 1,
        "unresolved_count": 1,
    }
    assert sweep["sweep_id"].startswith("gjfafsv1:sweep:")
    assert validate_gemini_json_flat_family_sweep_v1(sweep) == sweep

    tampered = deepcopy(sweep)
    tampered["metrics"]["mapping_count"] += 1
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_gemini_json_flat_family_sweep_v1(tampered)


def test_v3_root_prefers_exact_maximum_frontier_and_consumes_zero_provision_once() -> None:
    candidate = _evaluate_trading(_trading_page())
    assert candidate["status"] == READY
    root_receipts = [
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "EXPLICIT_NET_TOTAL"
    ]
    assert len(root_receipts) == 1
    assert root_receipts[0]["component_roles"] == [
        "DEBT_SECURITIES_GROUP",
        "EQUITY_SECURITIES_GROUP",
        "TRADING_SECURITIES_PROVISION_GROUP",
    ]
    assert (
        sum(
            equation["component_roles"].count("TRADING_SECURITIES_PROVISION_GROUP")
            for equation in candidate["closure_receipt"]["equations"]
        )
        == 1
    )


def test_v3_visible_subtotals_allow_one_exact_direct_frontier_per_lane() -> None:
    candidate = _evaluate_trading(_lane_specific_trading_page())
    assert candidate["status"] == READY
    equations = {
        equation["result_role"]: equation for equation in candidate["closure_receipt"]["equations"]
    }
    assert equations["EQUITY_SECURITIES_GROUP"] == {
        "component_roles": [
            "EQUITY_DOMESTIC_CREDIT_INSTITUTIONS",
            "EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            "OTHER_TRADING_SECURITIES_GROUP",
        ],
        "component_roles_by_lane": [
            [
                "EQUITY_DOMESTIC_CREDIT_INSTITUTIONS",
                "EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS",
            ],
            [
                "EQUITY_DOMESTIC_CREDIT_INSTITUTIONS",
                "EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS",
                "OTHER_TRADING_SECURITIES_GROUP",
            ],
        ],
        "component_row_ids_by_lane": [["r3", "r4"], ["r3", "r4", "r5"]],
        "lane_component_sums": [50, 70],
        "mode": "VISIBLE_RESULT_EXACTLY_CORROBORATED_BY_LANE_SPECIFIC_FRONTIERS",
        "result_coefficients": [50, 70],
        "result_role": "EQUITY_SECURITIES_GROUP",
        "result_row_id": "r2",
    }
    assert equations["EXPLICIT_NET_TOTAL"]["component_roles_by_lane"] == [
        [
            "DEBT_SECURITIES_GROUP",
            "EQUITY_SECURITIES_GROUP",
            "OTHER_TRADING_SECURITIES_GROUP",
            "TRADING_SECURITIES_PROVISION_GROUP",
        ],
        [
            "DEBT_SECURITIES_GROUP",
            "EQUITY_SECURITIES_GROUP",
            "TRADING_SECURITIES_PROVISION_GROUP",
        ],
    ]
    lane_use_counts: dict[tuple[str, int], int] = {}
    for equation in equations.values():
        roles_by_lane = equation.get("component_roles_by_lane")
        if roles_by_lane is None:
            roles_by_lane = [equation.get("component_roles", []) for _lane in range(2)]
        for lane, roles in enumerate(roles_by_lane):
            for role in roles:
                key = (role, lane)
                lane_use_counts[key] = lane_use_counts.get(key, 0) + 1
    assert max(lane_use_counts.values()) == 1


def test_v3_lane_specific_frontier_rejects_mismatch_and_duplicate_result_carrier() -> None:
    mismatch = _lane_specific_trading_page()
    mismatch["sections"][0]["tables"][0]["rows"][-1]["values_exact"][1] = "151"
    candidate = _evaluate_trading(mismatch)
    assert candidate["status"] == UNRESOLVED
    assert (
        "EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:EXPLICIT_NET_TOTAL:0" in candidate["reasons"]
    )

    duplicate = _lane_specific_trading_page()
    duplicate["sections"][0]["tables"][0]["rows"].append(
        {
            "hierarchy_path_exact": ["Giá trị còn lại"],
            "label_exact": "Giá trị còn lại",
            "row_kind": "TOTAL",
            "values_exact": ["145", "150"],
        }
    )
    candidate = _evaluate_trading(duplicate)
    assert candidate["status"] == UNRESOLVED
    assert "ROLE_OCCURRENCE_COUNT_ABOVE_ONE:EXPLICIT_NET_TOTAL:2" in candidate["reasons"]


def test_v3_lane_specific_frontier_rejects_same_role_consumed_twice_in_one_lane() -> None:
    page = _lane_specific_trading_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    rows[1]["values_exact"] = ["55", "70"]
    rows[-1]["values_exact"] = ["150", "155"]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == UNRESOLVED
    assert {
        "COMPONENT_ROLE_LANE_USE_COUNT_ABOVE_ONE:OTHER_TRADING_SECURITIES_GROUP:0:2",
        "COMPONENT_ROLE_LANE_USE_COUNT_ABOVE_ONE:OTHER_TRADING_SECURITIES_GROUP:1:2",
    } <= set(candidate["reasons"])


def test_v3_unowned_intermediate_subtotal_does_not_impersonate_family_total() -> None:
    page = _trading_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    rows[-1] = {
        "hierarchy_path_exact": [None],
        "label_exact": None,
        "row_kind": "SUBTOTAL",
        "values_exact": ["1", "1"],
    }
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    root = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "EXPLICIT_NET_TOTAL"
    )
    assert root["mode"] == "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"

    page["sections"][0]["tables"][0]["rows"][-1]["row_kind"] = "TOTAL"
    candidate = _evaluate_trading(page)
    assert candidate["status"] == UNRESOLVED
    assert (
        "EXACT_DIRECT_FRONTIER_SOLUTION_COUNT_NOT_ONE:EXPLICIT_NET_TOTAL:0" in candidate["reasons"]
    )


def test_v3_concatenated_structural_total_path_keeps_its_owner() -> None:
    page = _trading_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    rows.insert(
        1,
        {
            "hierarchy_path_exact": ["Chứng khoán nợTổng"],
            "label_exact": "Tổng",
            "row_kind": "TOTAL",
            "values_exact": ["100", "90"],
        },
    )
    rows.pop()
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    root = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "EXPLICIT_NET_TOTAL"
    )
    assert root["mode"] == "DERIVED_FROM_EXHAUSTIVE_VISIBLE_COMPONENTS"


def test_v3_root_raw_subset_requires_one_additive_child_not_provision_alone() -> None:
    candidate = _evaluate_trading(_trading_page(provision_only=True))
    assert candidate["status"] == UNRESOLVED
    assert "NO_EXHAUSTIVE_DIRECT_FRONTIER:EXPLICIT_NET_TOTAL" in candidate["reasons"]

    topology, evaluation, schema = _trading_specs()
    invalid = deepcopy(evaluation)
    invalid["hierarchical_closure_spec"]["equations"][-1]["component_role_alternatives"][-1][
        "minimum_additive_child_count"
    ] = "1"
    with pytest.raises(ValueError, match="alternative is invalid"):
        compile_gemini_json_flat_family_specs_v1(topology, invalid, schema)


def test_v3_label_only_groups_derive_from_complete_optional_children() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["1.1. Chứng khoán nợ"],
            "label_exact": "1.1. Chứng khoán nợ",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [
                "1.1. Chứng khoán nợ",
                "Chứng khoán nợ do các TCTD khác trong nước phát hành (i) (ii)",
            ],
            "label_exact": "Chứng khoán nợ do các TCTD khác trong nước phát hành (i) (ii)",
            "row_kind": "ITEM",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán vốn"],
            "label_exact": "Chứng khoán vốn",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [
                "Chứng khoán vốn",
                "Chứng khoán vốn do các TCKT trong nước phát hành",
            ],
            "label_exact": "Chứng khoán vốn do các TCKT trong nước phát hành",
            "row_kind": "ITEM",
            "values_exact": ["50", "40"],
        },
        {
            "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh"],
            "label_exact": "Dự phòng rủi ro chứng khoán kinh doanh",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [
                "Dự phòng rủi ro chứng khoán kinh doanh",
                "Dự phòng giảm giá chứng khoán kinh doanh",
            ],
            "label_exact": "Dự phòng giảm giá chứng khoán kinh doanh",
            "row_kind": "ITEM",
            "values_exact": ["-", "-"],
        },
        {
            "hierarchy_path_exact": ["Tổng chứng khoán kinh doanh"],
            "label_exact": "Tổng chứng khoán kinh doanh",
            "row_kind": "SUBTOTAL",
            "values_exact": ["150", "130"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["150", "130"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    equations = {
        equation["result_role"]: equation for equation in candidate["closure_receipt"]["equations"]
    }
    assert equations["DEBT_SECURITIES_GROUP"]["component_roles"] == [
        "DEBT_DOMESTIC_CREDIT_INSTITUTIONS"
    ]
    assert equations["EQUITY_SECURITIES_GROUP"]["component_roles"] == [
        "EQUITY_DOMESTIC_ECONOMIC_ORGANIZATIONS"
    ]
    assert equations["TRADING_SECURITIES_PROVISION_GROUP"]["component_roles"] == [
        "PROVISION_PRICE_DECREASE"
    ]


def test_v3_one_visible_listing_child_exactly_corroborates_its_group() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "GROUP",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán nợ", "Đã niêm yết"],
            "label_exact": "Đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["100", "90"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    assert any(mapping["role"] == "DEBT_LISTED" for mapping in candidate["mappings"])


def test_v3_expanded_tckt_annotation_and_short_other_label_are_structural() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "GROUP",
            "values_exact": ["150", "130"],
        },
        {
            "hierarchy_path_exact": [
                "Chứng khoán nợ",
                'Chứng khoán nợ do các tổ chức kinh tế ("TCKT") trong nước phát hành',
            ],
            "label_exact": ('Chứng khoán nợ do các tổ chức kinh tế ("TCKT") trong nước phát hành'),
            "row_kind": "ITEM",
            "values_exact": ["150", "130"],
        },
        {
            "hierarchy_path_exact": ["1.3. Chứng khoán khác"],
            "label_exact": "1.3. Chứng khoán khác",
            "row_kind": "ITEM",
            "values_exact": ["50", "40"],
        },
        {
            "hierarchy_path_exact": ["1.5. Dự phòng rủi ro chứng khoán kinh doanh"],
            "label_exact": "1.5. Dự phòng rủi ro chứng khoán kinh doanh",
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [
                "1.5. Dự phòng rủi ro chứng khoán kinh doanh",
                "Trong đó: - Dự phòng giảm giá",
            ],
            "label_exact": "Trong đó: - Dự phòng giảm giá",
            "row_kind": "ITEM",
            "values_exact": ["(10)", "(5)"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["190", "165"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "DEBT_DOMESTIC_ECONOMIC_ORGANIZATIONS",
        "TRADING_SECURITIES",
    }
    root_equation = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "EXPLICIT_NET_TOTAL"
    )
    assert "OTHER_TRADING_SECURITIES_GROUP" in root_equation["component_roles"]


def test_v3_zero_equivalent_frontiers_prefer_the_direct_structural_parent() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "GROUP",
            "values_exact": ["-", "-"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán nợ", "Trái phiếu Chính phủ"],
            "label_exact": "Trái phiếu Chính phủ",
            "row_kind": "ITEM",
            "values_exact": ["-", "-"],
        },
        {
            "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh"],
            "label_exact": "Dự phòng rủi ro chứng khoán kinh doanh",
            "row_kind": "SUBTOTAL",
            "values_exact": ["-", "-"],
        },
        {
            "hierarchy_path_exact": ["Giá trị thuần"],
            "label_exact": "Giá trị thuần",
            "row_kind": "TOTAL",
            "values_exact": ["-", "-"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    equations = {
        equation["result_role"]: equation for equation in candidate["closure_receipt"]["equations"]
    }
    assert equations["DEBT_SECURITIES_GROUP"]["component_roles"] == ["DEBT_GOVERNMENT"]
    assert equations["EXPLICIT_NET_TOTAL"]["component_roles"] == [
        "DEBT_SECURITIES_GROUP",
        "TRADING_SECURITIES_PROVISION_GROUP",
    ]


def test_v3_single_child_database_anchor_supports_group_or_family_parent() -> None:
    topology, evaluation, schema = _trading_specs()
    compiled = compile_gemini_json_flat_family_specs_v1(topology, evaluation, schema)
    government_aliases = compiled["aliases_by_role"]["DEBT_GOVERNMENT"]
    assert [
        compiled["aliases_by_role"]["DEBT_SECURITIES_GROUP"],
        government_aliases,
    ] in compiled["anchor_alias_groups"]
    assert [compiled["topology"]["parent"]["aliases"], government_aliases] in compiled[
        "anchor_alias_groups"
    ]


def test_v3_flat_listing_view_keeps_typed_roles_and_note_reference_suffix() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Trái phiếu đã niêm yết"],
            "label_exact": "Trái phiếu đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": ["Trái phiếu chưa niêm yết (Thuyết minh 8.3)"],
            "label_exact": "Trái phiếu chưa niêm yết (Thuyết minh 8.3)",
            "row_kind": "ITEM",
            "values_exact": ["20", "10"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán vốn đã niêm yết"],
            "label_exact": "Chứng khoán vốn đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["5", "4"],
        },
        {
            "hierarchy_path_exact": ["Giấy tờ có giá khác chưa niêm yết"],
            "label_exact": "Giấy tờ có giá khác chưa niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["2", "1"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["127", "105"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "DEBT_LISTED",
        "DEBT_UNLISTED",
        "EQUITY_LISTED",
        "OTHER_UNLISTED",
    }


def test_v3_concatenated_hierarchy_path_still_binds_generic_listing_children() -> None:
    page = _trading_page()
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": [
                "1.6 Thuyết minh tình trạng niêm yết Chứng khoán Nợ:+ Đã niêm yết"
            ],
            "label_exact": "+ Đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": [
                "1.6 Thuyết minh tình trạng niêm yết Chứng khoán Nợ:+ Chưa niêm yết"
            ],
            "label_exact": "+ Chưa niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["20", "10"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["120", "100"],
        },
    ]
    candidate = _evaluate_trading(page)
    assert candidate["status"] == READY
    assert {mapping["role"] for mapping in candidate["mappings"]} >= {
        "DEBT_LISTED",
        "DEBT_UNLISTED",
    }


def _trading_presentation_shadow_page() -> dict:
    page = _trading_page()
    disclosure = "Thuyết minh về tình trạng niêm yết của các chứng khoán kinh doanh"
    other = "Chứng khoán kinh doanh khác"
    page["sections"][0]["tables"][0]["rows"] = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "SUBTOTAL",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": [other],
            "label_exact": other,
            "row_kind": "SUBTOTAL",
            "values_exact": ["50", "40"],
        },
        {
            "hierarchy_path_exact": [disclosure],
            "label_exact": disclosure,
            "row_kind": "GROUP",
            "values_exact": [None, None],
        },
        {
            "hierarchy_path_exact": [disclosure, other],
            "label_exact": other,
            "row_kind": "SUBTOTAL",
            "values_exact": ["50", "40"],
        },
        {
            "hierarchy_path_exact": [disclosure, other, "+ Đã niêm yết"],
            "label_exact": "+ Đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["20", "10"],
        },
        {
            "hierarchy_path_exact": [disclosure, other, "+ Chưa niêm yết"],
            "label_exact": "+ Chưa niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["30", "30"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["150", "130"],
        },
    ]
    return page


def test_v3_exact_nested_presentation_shadow_corroborates_primary_group() -> None:
    candidate = _evaluate_trading(_trading_presentation_shadow_page())
    assert candidate["status"] == READY
    equation = next(
        equation
        for equation in candidate["closure_receipt"]["equations"]
        if equation["result_role"] == "OTHER_TRADING_SECURITIES_GROUP"
    )
    assert equation["component_roles"] == ["OTHER_LISTED", "OTHER_UNLISTED"]
    assert equation["result_row_id"] == "r2"
    assert equation["corroborating_result_row_ids"] == ["r4"]


@pytest.mark.parametrize("mutation", ["SHADOW_MISMATCH", "CHILD_MISMATCH"])
def test_v3_nested_presentation_shadow_fails_closed_unless_exact(mutation: str) -> None:
    page = _trading_presentation_shadow_page()
    rows = page["sections"][0]["tables"][0]["rows"]
    if mutation == "SHADOW_MISMATCH":
        rows[3]["values_exact"][0] = "51"
    else:
        rows[5]["values_exact"][0] = "29"
    candidate = _evaluate_trading(page)
    assert candidate["status"] == UNRESOLVED
    assert (
        "ROLE_OCCURRENCE_COUNT_ABOVE_ONE:OTHER_TRADING_SECURITIES_GROUP:2" in candidate["reasons"]
    )
