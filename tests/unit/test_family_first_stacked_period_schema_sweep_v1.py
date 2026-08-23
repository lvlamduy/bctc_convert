from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import family_first_stacked_period_schema_sweep_v1 as subject

ROOT = Path(__file__).resolve().parents[2]
CHALLENGER = json.loads(
    (
        ROOT
        / "docs/experiments/E-0162-family-first-derivative-hosted-gemma4-numeric-challenger-v1.json"
    ).read_text(encoding="utf-8")
)


def _install(monkeypatch: pytest.MonkeyPatch) -> None:
    projection = {"manifest_id": "manifest-1", "metrics": {"document_count": 2}}
    region = {"cluster_end_page_sequence_inclusive": 3, "page_sequence": 3}
    scans = (
        {
            "family_id": "DERIVATIVE_FINANCIAL_INSTRUMENTS",
            "regions": [region],
            "scan_id": "scan-1",
            "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
        },
        {
            "family_id": "DERIVATIVE_FINANCIAL_INSTRUMENTS",
            "regions": [],
            "scan_id": "scan-2",
            "status": "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
        },
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "project_authenticated_family_first_document_evidence_store_v1",
        lambda _cap: projection,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_topology_scans_v1",
        lambda _cap, _spec, jobs: scans,
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_packet_v1",
        lambda _cap, *, document_ordinal: {
            "document_ordinal": document_ordinal,
            "packet_id": f"packet-{document_ordinal}",
            "scope": "CONSOLIDATED",
        },
    )
    monkeypatch.setattr(
        subject.document_store_v1,
        "read_authenticated_family_first_document_evidence_snapshot_v1",
        lambda _cap, *, document_ordinal, selected_pages: {
            "joined_pages": [
                {"lines": [], "page_sequence": 1, "page_width": None},
                {"lines": [], "page_sequence": 2, "page_width": None},
                {"lines": [], "page_sequence": 3, "page_width": 1000},
            ]
        },
    )
    monkeypatch.setattr(
        subject.lane_axis_v1,
        "build_accounting_stacked_period_lane_axis_v1",
        lambda *_args: {"axis_id": "axis-1"},
    )
    monkeypatch.setattr(
        subject.schema_mapping_v1,
        "build_accounting_stacked_period_schema_mapping_v1",
        lambda *_args: {
            "mapping_id": "mapping-1",
            "mapping_proposals": [{"report_norm_id": 634}],
            "metrics": {
                "mapping_proposal_count": 1,
                "numeric_challenger_rescue_count": 0,
            },
            "unresolved_cells": [],
        },
    )
    monkeypatch.setattr(
        subject.unit_context_v1,
        "build_accounting_document_unit_context_v1",
        lambda *_args: {"context_id": "unit-1"},
    )


def _build(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    _install(monkeypatch)
    return subject.build_authenticated_family_first_stacked_period_schema_sweep_v1(
        object(),
        {"family_id": "DERIVATIVE_FINANCIAL_INSTRUMENTS"},
        {"layout": "test"},
        {"binding": "test"},
        [{"schema_id": 634, "scope": ["CONSOLIDATED", "SEPARATE"]}],
        CHALLENGER,
    )


def test_verified_and_bound_absence_trials_are_closed_and_replayable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build(monkeypatch)
    assert result["metrics"] == {
        "bounded_not_observed_count": 1,
        "document_count": 2,
        "numeric_challenger_rescue_count": 0,
        "unresolved_document_count": 0,
        "verified_document_count": 1,
        "verified_mapping_count": 1,
    }
    assert [item["status"] for item in result["trials"]] == [
        "VERIFIED_BY_CODEX",
        "NOT_OBSERVED_IN_BOUND_REPORT",
    ]
    assert (
        subject.validate_authenticated_family_first_stacked_period_schema_sweep_replay_v1(
            result,
            object(),
            {"family_id": "DERIVATIVE_FINANCIAL_INSTRUMENTS"},
            {"layout": "test"},
            {"binding": "test"},
            [{"schema_id": 634, "scope": ["CONSOLIDATED", "SEPARATE"]}],
            CHALLENGER,
        )
        == result
    )


def test_coordinated_metric_or_trial_promotion_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _build(monkeypatch)
    forged = copy.deepcopy(result)
    forged["metrics"]["verified_mapping_count"] = 2
    with pytest.raises(subject.FamilyFirstStackedPeriodSchemaSweepV1Error):
        subject._validate_result(forged)

    forged = copy.deepcopy(result)
    forged["trials"][1]["status"] = "VERIFIED_BY_CODEX"
    with pytest.raises(subject.FamilyFirstStackedPeriodSchemaSweepV1Error):
        subject._validate_result(forged)
