from __future__ import annotations

import pytest

from scripts.experiments.run_gemini_json_family_region_repair_worker_v1 import (
    RunGeminiJsonFamilyRegionRepairWorkerV1Error,
    _repair_attempt_outcome_v1,
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
