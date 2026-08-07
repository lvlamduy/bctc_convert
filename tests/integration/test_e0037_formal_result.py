from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

MAPPING_SEAL = {
    "path": "docs/experiments/E-0037-mbb-cdkt-mapping-only-seal.json",
    "sha256": "665aa1b3ac96881df0a4cd7b2f7da2425c3635ad1e8ea024e299b668c79ed0e5",
    "size_bytes": 6016,
}
POSTJOIN = {
    "path": "docs/experiments/E-0037-mbb-cdkt-sealed-evidence-mapping.json",
    "sha256": "a44146ff98ac9b33dd7f04037e69ba258ef7361dc158ecbd51a6688d7fbb6f7b",
    "size_bytes": 1_045_610,
}
SOURCE_STRUCTURE = {
    "path": "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/source_structure.json",
    "sha256": "ef098a659f8b557ac3a801edccfc7c0848be9a512b47ba7c9278cd3873f70728",
    "size_bytes": 136_042,
}
MAPPING_ONLY = {
    "path": "output/calibration/e0037-mbb-cdkt-sealed-evidence-mapping/mapping_only.json",
    "sha256": "e18f6b20825f93b20023c0d89caca1737481008b244696594852ca9fa972f99e",
    "size_bytes": 646_393,
}


def _read_exact_artifact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


def test_e0037_formal_seal_and_postjoin_result_are_hash_locked(project_root):
    seal = json.loads(_read_exact_artifact(project_root, MAPPING_SEAL))
    postjoin = json.loads(_read_exact_artifact(project_root, POSTJOIN))

    _read_exact_artifact(project_root, SOURCE_STRUCTURE)
    _read_exact_artifact(project_root, MAPPING_ONLY)

    assert seal["mapping_only"] == MAPPING_ONLY
    assert seal["input_hash_ledger"]["authentication_replay_inputs"]["source_structure"] == (
        SOURCE_STRUCTURE
    )
    assert seal["row_count"] == 64
    assert seal["schema_disposition_count"] == 77
    assert seal["row_mapping_status_counts"] == {
        "AMBIGUOUS_ACROSS_PATHS": 60,
        "NO_ADMISSIBLE_PAIR": 4,
    }
    assert seal["postjoin_access"] == {
        "deterministic_mapping_replay_byte_equal": True,
        "deterministic_mapping_replay_invocation_count": 1,
        "e0030_opened": False,
        "e0033_opened": False,
        "e0034_opened": False,
        "mapper_replay_used_to_change_mapping": False,
        "mapping_only_validated_before_postjoin_access": True,
    }

    assert postjoin["mapping_only"] == MAPPING_ONLY
    assert postjoin["mapping_only_seal"] == MAPPING_SEAL
    assert postjoin["input_hash_ledger"]["mapping_only"] == MAPPING_ONLY
    assert postjoin["input_hash_ledger"]["mapping_only_seal"] == MAPPING_SEAL
    assert postjoin["metrics"] == {
        "cell_count": 128,
        "cell_status_counts": {
            "DASH": 5,
            "OBSERVED_VALUE": 113,
            "UNRESOLVED": 10,
        },
        "mapping_status_counts": {
            "AMBIGUOUS_ACROSS_PATHS": 60,
            "NO_ADMISSIBLE_PAIR": 4,
        },
        "numeric_verification_status_counts": {
            "UNRESOLVED_BLANK_PENDING_ROW_SEMANTICS": 9,
            "UNRESOLVED_READER_DISAGREEMENT": 1,
            "VERIFIED_OBSERVED_DASH": 5,
            "VERIFIED_OBSERVED_VALUE": 113,
        },
        "output_status_counts": {"AMBIGUOUS": 120, "UNRESOLVED": 8},
        "period_axis_count": 4,
        "row_count": 64,
        "schema_disposition_count": 77,
        "transitive_e0033_binding_verified": True,
    }
    assert postjoin["access_order"] == {
        "e0030_opened_after_mapping_seal": True,
        "e0033_bound_transitively_through_e0034": True,
        "e0033_opened_directly": False,
        "e0034_opened_after_mapping_seal": True,
        "mapper_invocation_count": 0,
        "mapping_only_hash_validated_before_postjoin_open": True,
        "mapping_only_seal_validated_before_postjoin_open": True,
        "mapping_result_repaired_or_rerun": False,
        "review_or_history_opened": False,
    }
    assert postjoin["mapping"]["status"] == "AMBIGUOUS_MAPPING"
    assert postjoin["mapping"]["score_margin"] == 0.1
    assert postjoin["mapping"]["automatic_selection_allowed"] is False
    assert postjoin["period_unit_summary"] == {
        "canonical_unit": "VND",
        "comparative_period_end": "2025-12-31",
        "comparative_period_start": "2025-12-31",
        "current_period_end": "2026-03-31",
        "current_period_start": "2026-03-31",
        "matched_unit_anchor": "triệu đồng",
        "period_type": "SNAPSHOT",
        "raw_unit_text": "triu đồng",
        "report_scope": "UNKNOWN",
        "unit_multiplier": 1_000_000,
    }

    rows = postjoin["rows"]
    cells = postjoin["cells"]
    assert Counter(row["mapping"]["status"] for row in rows) == {
        "AMBIGUOUS_ACROSS_PATHS": 60,
        "NO_ADMISSIBLE_PAIR": 4,
    }
    assert all(row["mapping"]["selected_report_norm_id"] is None for row in rows)
    assert Counter(cell["output_status"] for cell in cells) == {
        "AMBIGUOUS": 120,
        "UNRESOLVED": 8,
    }
    assert all(cell["selected_report_norm_id"] is None for cell in cells)
    assert all(
        cell[field] is None
        for cell in cells
        for field in (
            "selected_raw_value",
            "selected_normalized_value",
            "displayed_unit_value",
            "canonical_unit_value",
        )
    )

    verified_values = [
        cell for cell in cells if cell["numeric_verification_status"] == "VERIFIED_OBSERVED_VALUE"
    ]
    assert len(verified_values) == 113
    assert all(cell["visible_raw_value"] for cell in verified_values)
    assert all(
        cell["numeric_evidence"]["selected_raw_value"] == cell["visible_raw_value"]
        and cell["numeric_evidence"]["normalized_numeric_value"] is not None
        for cell in verified_values
    )


def test_e0037_source_and_mapping_s3_snapshot_registry_is_exact(project_root):
    registry = project_root / "data/registered/s3_artifact_snapshot_registry.jsonl"
    records = [json.loads(line) for line in registry.read_text(encoding="utf-8").splitlines()]
    snapshot_id = "20260807T170440Z-e0037-source-and-mapping-seal-e18f6b20825f"
    matches = [record for record in records if record.get("artifact_snapshot_id") == snapshot_id]

    assert matches == [
        {
            "artifact_snapshot_id": snapshot_id,
            "dataset_role": "CALIBRATION",
            "file_count": 2,
            "format_version": 1,
            "git_commit": "4e475d503ee02328241140faba3399387d18f2dd",
            "hydrate_probe": {
                "logical_paths": [SOURCE_STRUCTURE["path"], MAPPING_ONLY["path"]],
                "restored_file_count": 2,
                "reused_file_count_on_second_hydrate": 2,
                "sealed_hashes_match": True,
                "status": "PASS",
            },
            "label": "e0037-source-and-mapping-seal",
            "manifest": {
                "key": (
                    "bctc-ai/artifact-snapshots/"
                    f"{snapshot_id}/"
                    "manifest-b7b2b5bd4249d93fc8bca2210228ffd000eb36e5ebc0bb7167dde4e774478c8c.json"
                ),
                "sha256": ("b7b2b5bd4249d93fc8bca2210228ffd000eb36e5ebc0bb7167dde4e774478c8c"),
            },
            "parent_full_snapshot": {
                "manifest_sha256": (
                    "74be9ea09905f0c7842d5a0b46bfe44f3fc5f32cc2c15b5040efcc4e99e8981b"
                ),
                "snapshot_id": "20260806T050030130746Z-4a469fab2334",
            },
            "policy": "S3_BOUNDED_ARTIFACT_SNAPSHOT_V1",
            "restore_verified": True,
            "run_record": {
                "key": (
                    "bctc-ai/artifact-runs/"
                    f"{snapshot_id}/"
                    "run-68b35baa1f3993021db5e550b87bd42af515076dd84e2e968248a27d02a22a34.json"
                ),
                "sha256": ("68b35baa1f3993021db5e550b87bd42af515076dd84e2e968248a27d02a22a34"),
            },
            "total_bytes": SOURCE_STRUCTURE["size_bytes"] + MAPPING_ONLY["size_bytes"],
        }
    ]
