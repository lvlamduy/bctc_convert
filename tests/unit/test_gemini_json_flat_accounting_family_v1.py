from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from bctc_ai.evaluation.gemini_json_flat_accounting_family_v1 import (
    NOT_OBSERVED,
    READY,
    UNRESOLVED,
    build_gemini_json_flat_family_sweep_v1,
    compile_gemini_json_flat_family_specs_v1,
    evaluate_gemini_json_flat_family_table_v1,
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
