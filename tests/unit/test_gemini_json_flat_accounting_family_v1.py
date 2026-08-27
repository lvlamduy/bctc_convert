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
