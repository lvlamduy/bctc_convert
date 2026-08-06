from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file


def test_e0023_ordered_schema_graph_is_hash_locked_and_fail_closed(project_root):
    artifact_path = project_root / "docs/experiments/E-0023-ordered-schema-graph.json"
    assert sha256_file(artifact_path) == (
        "87121a2eee5e29213e06c43bcd92db14d62291fbf79afced7f5c9eec90ae5bd1"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["format_version"] == 1
    assert artifact["experiment_id"] == "E-0023"
    assert artifact["dataset_role"] == "LOGIC_DEVELOPMENT"
    assert artifact["status"] == ("PASS_LOGIC_DEVELOPMENT_NO_PRODUCTION_CONFIDENCE_PROMOTION")
    assert artifact["code"] == {
        "git_commit": "48043d0335448b051f79b2768695a30ddc84b3b4",
        "git_dirty": False,
    }
    assert artifact["source_documents_read"] == []
    assert "neither real-document OCR accuracy" in artifact["claim_boundary"]
    assert "E-0022 remains frozen" in artifact["claim_boundary"]

    assert artifact["metrics"] == {
        "baseline": {
            "correct_pairs": 3,
            "duplicate_schema_assignments": 3,
            "false_positive_pairs": 3,
            "precision": 0.5,
            "predicted_pairs": 6,
            "recall": 1.0,
            "retained_extra_pdf_rows": 0,
        },
        "ordered_subgraph": {
            "correct_pairs": 3,
            "duplicate_schema_assignments": 0,
            "false_positive_pairs": 0,
            "precision": 1.0,
            "predicted_pairs": 3,
            "recall": 1.0,
            "retained_extra_pdf_rows": 3,
        },
    }
    assert artifact["delta"] == {
        "duplicate_schema_assignments": -3,
        "false_positive_pairs": -3,
        "precision": 0.5,
        "retained_extra_pdf_rows": 3,
    }
    ordered = artifact["ordered_subgraph"]
    assert ordered["status"] == "RESOLVED"
    assert ordered["automatic_selection_allowed_for_fixture"] is True
    assert ordered["score_margin"] == 1.43
    assert [(item["row_id"], item["schema_id"]) for item in ordered["best_path"]["matches"]] == [
        ("p1", 50),
        ("p3", 700),
        ("p5", 10),
    ]
    assert ordered["best_path"]["skipped_pdf_row_ids"] == ["p0", "p2", "p4"]
    assert ordered["best_path"]["structural_issues"] == []
    assert ordered["search"] == {
        "algorithm": "K_BEST_MONOTONE_DYNAMIC_PROGRAMMING_FAIL_CLOSED",
        "beam_width_per_cell": 32,
        "dp_cells": 28,
        "generated_states": 326,
        "pdf_rows": 6,
        "retained_states": 228,
        "schema_nodes": 3,
    }

    safety = artifact["safety_fixtures"]
    assert safety["ambiguity_fixture"] == {
        "automatic_selection_allowed": False,
        "score_margin": 0.0,
        "status": "AMBIGUOUS_MAPPING",
        "top_schema_ids": [10, 900],
    }
    assert safety["verified_parent_fixture"]["selected_schema_id"] == 801
    assert (
        safety["verified_parent_fixture"]["wrong_semantic_candidate_appears_in_any_path"] is False
    )
    assert safety["off_balance_fixture"]["status"] == "OUT_OF_SCOPE_FOR_TARGET_TEMPLATE"
    assert safety["off_balance_fixture"]["matched_pairs"] == 0

    assert artifact["real_schema_graph"]["cdkt_node_count"] == 77
    assert artifact["real_schema_graph"]["non_numeric_workbook_sequence"] == [4337, 4373, 4338]
    assert artifact["real_schema_graph"]["fixed_asset_parent_ids"] == {
        "4367": 4328,
        "4369": 4329,
        "4371": 4330,
    }
    assert artifact["schema_registry"] == {
        "item_count": 1593,
        "numeric_report_norm_id_sort_used": False,
        "tm_1944_present": True,
    }
    assert all(value is False for value in artifact["authority"].values())
    for record in artifact["config"].values():
        assert sha256_file(project_root / record["path"]) == record["sha256"]
    for relative_path, digest in artifact["algorithm_files_sha256"].items():
        assert sha256_file(project_root / relative_path) == digest
