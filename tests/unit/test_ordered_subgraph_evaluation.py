from __future__ import annotations

from bctc_ai.evaluation.ordered_subgraph_evaluation import evaluate_ordered_subgraph_logic


def test_e0023_logic_evaluation_has_expected_before_after_and_safety(project_root):
    result = evaluate_ordered_subgraph_logic(
        project_root,
        project_root / "config/experiments/e0023-ordered-schema-graph.yaml",
    )

    assert result["status"] == "PASS_LOGIC_DEVELOPMENT_NO_PRODUCTION_CONFIDENCE_PROMOTION"
    assert result["metrics"]["baseline"] == {
        "predicted_pairs": 6,
        "correct_pairs": 3,
        "false_positive_pairs": 3,
        "duplicate_schema_assignments": 3,
        "retained_extra_pdf_rows": 0,
        "precision": 0.5,
        "recall": 1.0,
    }
    assert result["metrics"]["ordered_subgraph"] == {
        "predicted_pairs": 3,
        "correct_pairs": 3,
        "false_positive_pairs": 0,
        "duplicate_schema_assignments": 0,
        "retained_extra_pdf_rows": 3,
        "precision": 1.0,
        "recall": 1.0,
    }
    assert result["delta"] == {
        "precision": 0.5,
        "false_positive_pairs": -3,
        "duplicate_schema_assignments": -3,
        "retained_extra_pdf_rows": 3,
    }
    assert result["ordered_subgraph"]["score_margin"] == 1.43
    assert result["safety_fixtures"]["ambiguity_fixture"]["status"] == "AMBIGUOUS_MAPPING"
    assert result["safety_fixtures"]["verified_parent_fixture"]["selected_schema_id"] == 801
    assert result["safety_fixtures"]["off_balance_fixture"]["status"] == (
        "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"
    )
    assert result["real_schema_graph"]["non_numeric_workbook_sequence"] == [4337, 4373, 4338]
    assert result["schema_registry"]["tm_1944_present"] is True
    assert all(value is False for value in result["authority"].values())
