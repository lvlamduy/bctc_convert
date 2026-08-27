from __future__ import annotations

import pytest

from scripts.experiments.run_gemini_json_family_region_repair_worker_v1 import (
    RunGeminiJsonFamilyRegionRepairWorkerV1Error,
    _repair_attempt_outcome_v1,
    _targeted_repair_is_accepted,
)


@pytest.mark.parametrize("thinking_level", ["low", "medium"])
def test_unchanged_source_escalates_until_final_bounded_read(thinking_level: str) -> None:
    assert (
        _repair_attempt_outcome_v1(
            resolved=False,
            stable_source=True,
            thinking_level=thinking_level,
        )
        == "RETRYABLE_VALIDATION_FAILURE"
    )


def test_only_high_may_seal_unchanged_source_evidence() -> None:
    assert (
        _repair_attempt_outcome_v1(
            resolved=False,
            stable_source=True,
            thinking_level="high",
        )
        == "STABLE_SOURCE_EVIDENCE"
    )
    assert (
        _repair_attempt_outcome_v1(
            resolved=True,
            stable_source=False,
            thinking_level="low",
        )
        == "RESOLVED"
    )


def test_repair_outcome_rejects_unknown_reasoning_level() -> None:
    with pytest.raises(
        RunGeminiJsonFamilyRegionRepairWorkerV1Error,
        match="outcome input is invalid",
    ):
        _repair_attempt_outcome_v1(
            resolved=False,
            stable_source=False,
            thinking_level="extreme",
        )


def test_unmatched_label_repair_is_not_accepted_while_target_row_remains_unbound() -> None:
    plan = {
        "trigger_kinds": ["UNMATCHED_SOURCE_LABEL"],
        "trigger_reasons": [
            "FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED",
            "UNBOUND_VISIBLE_NUMERIC_ROWS:2",
        ],
    }
    candidate = {
        "reasons": [
            "FAMILY_ROOT_IS_NOT_HIERARCHICALLY_RESOLVED",
            "UNBOUND_VISIBLE_NUMERIC_ROWS:2",
        ],
        "status": "UNRESOLVED_REQUIRES_NEW_EVIDENCE",
    }
    assert not _targeted_repair_is_accepted(plan, candidate)
