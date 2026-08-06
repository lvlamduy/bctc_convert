from __future__ import annotations

from bctc_ai.evaluation.deepseek_line_benchmark import (
    _commit_identity_matches,
    semantic_reader_gate,
    statement_result_summary,
)


def _score(*, cer, titles, empty_or_truncated):
    return {
        "aggregate": {
            "character_error_rate": cer,
            "title_exact_line_count": titles,
            "empty_or_suffix_truncated_count": empty_or_truncated,
        }
    }


def test_commit_identity_accepts_only_safe_prefix_of_full_recorded_commit():
    commit = "a44b08bdd1378e4cd1524ee02d426ad6dbb4e2c0"

    assert _commit_identity_matches(commit, "a44b08b") is True
    assert _commit_identity_matches(commit, commit) is True
    assert _commit_identity_matches(commit, "a44b08c") is False
    assert _commit_identity_matches(commit, "a44b08") is False
    assert _commit_identity_matches("a44b08b", "a44b08b") is False
    assert _commit_identity_matches(commit, None) is False


def test_semantic_gate_requires_quality_structure_and_output_budget_together():
    baseline = _score(cer=0.15, titles=0, empty_or_truncated=0)
    challenger = _score(cer=0.01, titles=5, empty_or_truncated=0)

    passed = semantic_reader_gate(
        baseline,
        challenger,
        structural_rejection_count=0,
        maximum_raw_output_characters=55,
        maximum_allowed_characters=512,
    )
    structural_failure = semantic_reader_gate(
        baseline,
        challenger,
        structural_rejection_count=1,
        maximum_raw_output_characters=55,
        maximum_allowed_characters=512,
    )

    assert all(passed.values())
    assert structural_failure["zero_structural_rejections"] is False
    assert sum(not value for value in structural_failure.values()) == 1


def test_statement_summary_excludes_raw_values_and_preserves_scope_sequence_contract():
    result = {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        "runner_up_margin": 8.5,
        "block": {
            "mapping_eligible_pages_by_statement_type": {"CDKT": [1], "KQKD": [3]},
            "off_balance_excluded_pages": [2],
            "notes_boundary_page": 5,
            "raw_values": [123],
        },
        "cash_flow": {"method": "DIRECT", "values": [456]},
    }

    assert statement_result_summary(result) == {
        "status": "ACCEPTED_MULTI_SIGNAL_STATEMENT_BLOCK",
        "mapping_eligible_pages_by_statement_type": {"CDKT": [1], "KQKD": [3]},
        "off_balance_excluded_pages": [2],
        "notes_boundary_page": 5,
        "runner_up_margin": 8.5,
        "cash_flow_method": "DIRECT",
    }
