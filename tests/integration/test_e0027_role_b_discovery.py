from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0027_role_b_v3_discovery_baseline_is_hash_locked(project_root):
    artifact_path = (
        project_root
        / "docs/experiments/E-0027-mbb-q1-2026-role-b-discovery-v3.json"
    )
    assert sha256_file(artifact_path) == (
        "9ccfd0faf869adee4cb885a4a87a32c86354101e82adc1d62c32e4ce7e9089c8"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["experiment_id"] == "E-0027"
    assert artifact["state"] == "ROLE_B_DISCOVERY_V3_SEALED_UNRESOLVED"
    assert artifact["dataset_role"] == "CALIBRATION"
    assert artifact["capture_git_commit"] == (
        "791b48a6263060db97016a73e1ae2cf76a047e75"
    )
    assert artifact["ocr_batch_manifest"]["sha256"] == (
        "0d94762ba4a0d383793fe93a56e48fa7b79d6a3f7faaf62e9dcf40935b8c2889"
    )
    assert artifact["role_b_policy"] == {
        "e0022_evidence_loaded": False,
        "excel_export_invoked": False,
        "historical_values_loaded": False,
        "human_review_loaded": False,
        "mapping_invoked": False,
        "numeric_extraction_invoked": False,
        "semantic_reader_invoked": False,
    }

    summary = artifact["summary"]
    assert summary["status"] == "UNRESOLVED"
    assert summary["algorithm_revision"] == 3
    assert summary["candidate_path_count"] == 0
    assert summary["mapping_eligible_page_count"] == 0
    assert [
        (item["page"], item["statement_type"], item["scope"])
        for item in summary["local_acceptances"]
    ] == [
        (3, "CDKT", "MAIN_STATEMENT"),
        (4, "CDKT", "MAIN_STATEMENT"),
        (5, "CDKT", "OFF_BALANCE_SHEET"),
        (6, "KQKD", "MAIN_STATEMENT"),
        (7, "LCTT", "MAIN_STATEMENT"),
        (8, "LCTT", "MAIN_STATEMENT"),
    ]
    page_9 = next(item for item in summary["notes_candidates"] if item["page"] == 9)
    assert page_9 == {
        "accounting_hit_count": 1,
        "independent_signal_groups": [
            "HEADER_IDENTITY",
            "REPORTING_PERIOD",
            "NOTES_STRUCTURE",
        ],
        "locally_accepted": False,
        "page": 9,
        "score": 4.75,
    }
