from __future__ import annotations

import pytest

from scripts.experiments.run_gemini_json_family_region_repair_worker_v1 import (
    RunGeminiJsonFamilyRegionRepairWorkerV1Error,
    _repair_attempt_outcome_v1,
    _segment_repair_mode_v1,
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


def test_segment_plan_rejects_same_family_nonsegment_compilation() -> None:
    with pytest.raises(
        RunGeminiJsonFamilyRegionRepairWorkerV1Error,
        match="segment-report modes disagree",
    ):
        _segment_repair_mode_v1(
            plan={"family_id": "CONSOLIDATED_SEGMENT_REPORT"},
            compiled={
                "segment_report_mode": False,
                "topology": {"family_id": "CONSOLIDATED_SEGMENT_REPORT"},
            },
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


def test_table_title_repair_requires_parent_reason_removed_before_staged_followup() -> None:
    plan = {
        "trigger_kinds": ["TABLE_EXPLICIT_FAMILY_TITLE_MISSING"],
        "trigger_reasons": [
            "FAMILY_PARENT_NOT_VISIBLE_IN_SECTION_TABLE_OR_UNIQUE_ROW",
            "UNBOUND_VISIBLE_NUMERIC_ROWS:2",
        ],
    }
    still_missing = {
        "reasons": plan["trigger_reasons"],
        "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
    }
    assert not _targeted_repair_is_accepted(plan, still_missing)
    title_fixed = {
        "reasons": ["UNBOUND_VISIBLE_NUMERIC_ROWS:2"],
        "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
    }
    assert _targeted_repair_is_accepted(plan, title_fixed)


def test_section_narrative_repair_requires_footnote_reason_removed() -> None:
    plan = {
        "trigger_kinds": ["SECTION_NARRATIVE_SOURCE_INCOMPLETE"],
        "trigger_reasons": ["TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"],
    }
    still_missing = {
        "reasons": ["TITLE_FOOTNOTE_NARRATIVE_SOURCE_NOT_EXACT"],
        "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
    }
    assert not _targeted_repair_is_accepted(plan, still_missing)
    resolved = {
        "reasons": [],
        "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    }
    assert _targeted_repair_is_accepted(plan, resolved)


def _segment_plan(*, scope: str, reasons: list[str], required_status: str) -> dict:
    period = scope == "TABLE_PERIOD_AXIS"
    applicable = (
        {
            "SEGMENT_COLUMN_PERIOD_AMBIGUOUS",
            "SEGMENT_PERIOD_END_NOT_RESOLVED",
            "SEGMENT_PERIOD_NOT_RESOLVED",
            "SEGMENT_TABLE_TITLE_PERIOD_AMBIGUOUS",
        }
        if period
        else {
            "SEGMENT_MONEY_CELL_AMBIGUOUS",
            "SEGMENT_MONEY_CELL_INVALID",
        }
    )
    return {
        "acceptance_policy": {
            "candidate_identity_must_replay": True,
            "forbid_arithmetic_backsolve": True,
            "forbid_new_unresolved_reasons": True,
            "promote_when_targeted_ocr_reason_is_removed": True,
            "require_candidate_status": required_status,
        },
        "family_id": "CONSOLIDATED_SEGMENT_REPORT",
        "repair_scope": scope,
        "targeted_trigger_reasons": sorted(set(reasons) & applicable),
        "trigger_kinds": ["TABLE_PERIOD_AXIS_INCOMPLETE" if period else "INVALID_MONEY_CELL"],
        "trigger_reasons": reasons,
    }


@pytest.mark.parametrize(
    "reason",
    [
        "SEGMENT_COLUMN_PERIOD_AMBIGUOUS",
        "SEGMENT_PERIOD_END_NOT_RESOLVED",
        "SEGMENT_PERIOD_NOT_RESOLVED",
        "SEGMENT_TABLE_TITLE_PERIOD_AMBIGUOUS",
    ],
)
def test_segment_period_repair_rejects_unchanged_typed_reason(reason: str) -> None:
    plan = _segment_plan(
        scope="TABLE_PERIOD_AXIS",
        reasons=[reason],
        required_status="READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    )
    assert not _targeted_repair_is_accepted(
        plan,
        {"reasons": [reason], "status": "UNRESOLVED_GEMINI_JSON_FAMILY"},
    )


def test_segment_money_repair_requires_exact_scope_reason_and_status() -> None:
    reason = "SEGMENT_MONEY_CELL_INVALID"
    plan = _segment_plan(
        scope="ROW_VALUES",
        reasons=[reason],
        required_status="READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
    )
    assert not _targeted_repair_is_accepted(
        plan,
        {"reasons": [reason], "status": "UNRESOLVED_GEMINI_JSON_FAMILY"},
    )
    wrong_scope = {**plan, "repair_scope": "TABLE_PERIOD_AXIS"}
    assert not _targeted_repair_is_accepted(
        wrong_scope,
        {"reasons": [], "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"},
    )
    assert _targeted_repair_is_accepted(
        plan,
        {"reasons": [], "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY"},
    )


def test_segment_period_stage_honors_explicit_unresolved_required_status() -> None:
    reasons = ["SEGMENT_MONEY_CELL_AMBIGUOUS", "SEGMENT_PERIOD_NOT_RESOLVED"]
    plan = _segment_plan(
        scope="TABLE_PERIOD_AXIS",
        reasons=reasons,
        required_status="UNRESOLVED_GEMINI_JSON_FAMILY",
    )
    assert _targeted_repair_is_accepted(
        plan,
        {
            "reasons": ["SEGMENT_MONEY_CELL_AMBIGUOUS"],
            "status": "UNRESOLVED_GEMINI_JSON_FAMILY",
        },
    )
    assert not _targeted_repair_is_accepted(
        plan,
        {
            "reasons": ["SEGMENT_MONEY_CELL_AMBIGUOUS"],
            "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
        },
    )
