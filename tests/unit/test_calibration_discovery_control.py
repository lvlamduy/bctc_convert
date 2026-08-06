from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import calibration_discovery_control
from bctc_ai.evaluation.calibration_discovery_control import (
    CalibrationDiscoveryControlError,
    capture_e0027_role_b_discovery,
    summarize_discovery_result,
)


def test_discovery_summary_separates_local_evidence_from_global_eligibility():
    result = {
        "status": "UNRESOLVED",
        "algorithm_revision": 3,
        "candidate_path_count": 0,
        "runner_up_margin": None,
        "errors": ["no complete path"],
        "page_signals": [
            {
                "page": 3,
                "candidates": [
                    {
                        "page_type": "CDKT",
                        "scope": "MAIN_STATEMENT",
                        "score": 8.5,
                        "locally_accepted": True,
                        "independent_signal_groups": ["HEADER_IDENTITY", "ACCOUNTING_ROWS"],
                        "accounting_hits": [{}, {}],
                    },
                    {
                        "page_type": "TM",
                        "score": 1.25,
                        "locally_accepted": False,
                        "independent_signal_groups": ["REPORTING_PERIOD"],
                        "accounting_hits": [],
                    },
                ],
            },
            {
                "page": 9,
                "candidates": [
                    {
                        "page_type": "TM",
                        "score": 4.75,
                        "locally_accepted": False,
                        "independent_signal_groups": [
                            "HEADER_IDENTITY",
                            "REPORTING_PERIOD",
                            "NOTES_STRUCTURE",
                        ],
                        "accounting_hits": [{}],
                    }
                ],
            },
        ],
    }

    summary = summarize_discovery_result(result)

    assert summary["mapping_eligible_page_count"] == 0
    assert summary["local_acceptances"] == [
        {
            "page": 3,
            "statement_type": "CDKT",
            "scope": "MAIN_STATEMENT",
            "score": 8.5,
            "independent_signal_groups": ["HEADER_IDENTITY", "ACCOUNTING_ROWS"],
            "accounting_hit_count": 2,
        }
    ]
    assert summary["notes_candidates"][-1]["accounting_hit_count"] == 1
    assert summary["notes_candidates"][-1]["locally_accepted"] is False


def test_e0027_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(calibration_discovery_control, "_git", lambda *_args: " M file")

    with pytest.raises(CalibrationDiscoveryControlError, match="requires clean Git code"):
        capture_e0027_role_b_discovery(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0027-mbb-q1-2026-end-to-end.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/unused-e0027.json"),
        )


def test_e0027_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(calibration_discovery_control, "_git", lambda *_args: "")

    with pytest.raises(CalibrationDiscoveryControlError, match="refusing to overwrite"):
        capture_e0027_role_b_discovery(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0027-mbb-q1-2026-end-to-end.yaml"
            ),
            batch_root=Path("unused"),
            output_path=Path("docs/experiments/E-0026-REPLAY.md"),
        )
