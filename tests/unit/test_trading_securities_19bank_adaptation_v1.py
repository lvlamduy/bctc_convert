from __future__ import annotations

import json
from pathlib import Path

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    READY,
    UNRESOLVED,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
)

ROOT = Path(__file__).resolve().parents[2]


def _compiled_specs() -> dict:
    specs = [
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (
            "config/families/tm-trading-securities-topology-v1.json",
            "config/families/tm-trading-securities-evaluation-v1.json",
            "config/families/tm-trading-securities-schema-binding-v1.json",
        )
    ]
    return compile_gemini_json_flat_family_specs_v1(*specs)


def _evaluate(rows: list[dict]) -> dict:
    page = {
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
                        "rows": rows,
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
    return evaluate_gemini_json_flat_family_table_v1(
        page_json=page,
        page_json_version_id="gfpstorev1:json:" + "e" * 64,
        physical_page=1,
        section_id="s1",
        table_id="t1",
        compiled_specs=_compiled_specs(),
    )


def test_issuer_view_emits_schema_group_and_provision_ids_from_exact_rows() -> None:
    result = _evaluate(
        [
            {
                "hierarchy_path_exact": ["Chứng khoán nợ"],
                "label_exact": "Chứng khoán nợ",
                "row_kind": "GROUP",
                "values_exact": ["100", "90"],
            },
            {
                "hierarchy_path_exact": ["Chứng khoán nợ", "Chứng khoán Chính phủ"],
                "label_exact": "Chứng khoán Chính phủ",
                "row_kind": "ITEM",
                "values_exact": ["100", "90"],
            },
            {
                "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh"],
                "label_exact": "Dự phòng rủi ro chứng khoán kinh doanh",
                "row_kind": "GROUP",
                "values_exact": ["(10)", "(9)"],
            },
            {
                "hierarchy_path_exact": [
                    "Dự phòng rủi ro chứng khoán kinh doanh",
                    "Dự phòng chung",
                ],
                "label_exact": "Dự phòng chung",
                "row_kind": "ITEM",
                "values_exact": ["(10)", "(9)"],
            },
            {
                # Mirrors a provider representation where the final unlabeled
                # net total retained the preceding provision-group ancestor.
                "hierarchy_path_exact": ["Dự phòng rủi ro chứng khoán kinh doanh", None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["90", "81"],
            },
        ]
    )

    assert result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        592,
        594,
        595,
        612,
        614,
    ]
    contextual = {
        mapping["report_norm_id"]: mapping
        for mapping in result["mappings"]
        if "presentation_context" in mapping
    }
    assert contextual[612]["presentation_context"] == "ISSUER_CLASSIFICATION"
    assert contextual[612]["source_role"] == "TRADING_SECURITIES_PROVISION_GROUP"
    assert [value["coefficient"] for value in contextual[612]["values"]] == [-10, -9]


def test_listing_view_emits_schema_parent_before_listed_and_unlisted_children() -> None:
    result = _evaluate(
        [
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
                "values_exact": ["60", "50"],
            },
            {
                "hierarchy_path_exact": ["Chứng khoán nợ", "Chưa niêm yết"],
                "label_exact": "Chưa niêm yết",
                "row_kind": "ITEM",
                "values_exact": ["40", "40"],
            },
            {
                "hierarchy_path_exact": [None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["100", "90"],
            },
        ]
    )

    assert result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        592,
        617,
        618,
        619,
    ]
    parent = next(mapping for mapping in result["mappings"] if mapping["report_norm_id"] == 617)
    assert parent["presentation_context"] == "LISTING_CLASSIFICATION"
    assert parent["source_role"] == "DEBT_SECURITIES_GROUP"


def test_short_listing_label_under_equity_group_is_not_treated_as_absence() -> None:
    result = _evaluate(
        [
            {
                "hierarchy_path_exact": ["Chứng khoán vốn"],
                "label_exact": "Chứng khoán vốn",
                "row_kind": "GROUP",
                "values_exact": ["58.183", "1"],
            },
            {
                "hierarchy_path_exact": ["Chứng khoán vốn", "Niêm yết"],
                "label_exact": "Niêm yết",
                "row_kind": "ITEM",
                "values_exact": ["58.183", "1"],
            },
            {
                "hierarchy_path_exact": [None],
                "label_exact": None,
                "row_kind": "TOTAL",
                "values_exact": ["58.183", "1"],
            },
        ]
    )

    assert result["status"] == READY
    assert [mapping["report_norm_id"] for mapping in result["mappings"]] == [
        592,
        620,
        621,
    ]


def test_mixed_presentation_evidence_does_not_guess_one_schema_parent_branch() -> None:
    rows = [
        {
            "hierarchy_path_exact": ["Chứng khoán nợ"],
            "label_exact": "Chứng khoán nợ",
            "row_kind": "GROUP",
            "values_exact": ["100", "90"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán nợ", "Chứng khoán Chính phủ"],
            "label_exact": "Chứng khoán Chính phủ",
            "row_kind": "ITEM",
            "values_exact": ["40", "30"],
        },
        {
            "hierarchy_path_exact": ["Chứng khoán nợ", "Đã niêm yết"],
            "label_exact": "Đã niêm yết",
            "row_kind": "ITEM",
            "values_exact": ["60", "60"],
        },
        {
            "hierarchy_path_exact": [None],
            "label_exact": None,
            "row_kind": "TOTAL",
            "values_exact": ["100", "90"],
        },
    ]
    result = _evaluate(rows)

    # The two axes must not be mixed into one additive frontier or guessed into
    # either schema representation branch.
    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert "HIERARCHICAL_SOLUTION_COUNT_NOT_ONE:0" in result["reasons"]
