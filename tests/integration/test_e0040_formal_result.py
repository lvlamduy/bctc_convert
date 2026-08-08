from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

CAPTURE_COMMIT = "18aca8942faf5d47e1ac5f049045d7a7a297b5fc"
MAPPING = {
    "path": "output/calibration/e0040-mbb-cdkt-formal-mapping/mapping_only.json",
    "sha256": "8def983007fc3aacf59351395426d5246ad3f28d605442f590de55eaf396cb0d",
    "size_bytes": 1_157_172,
}
SEAL = {
    "path": "docs/experiments/E-0040-mbb-cdkt-formal-mapping-seal.json",
    "sha256": "68306f7f540faa77d6e2e383927eae23fc3724cfdc8c53cded978a86f3a00b29",
    "size_bytes": 7_611,
}
CONTROL = {
    "path": "config/experiments/e0040-mbb-cdkt-formal-mapping.yaml",
    "sha256": "79f25408c79ec0e28584f34340038325df3da2756d840f5ed0bd796ad557a0a0",
    "size_bytes": 8_987,
}
IMPLEMENTATION = {
    "capture_script": {
        "path": "scripts/experiments/capture_e0040_mbb_cdkt_formal_mapping.py",
        "sha256": "9344ffb7d131f4d4decadb15d314e35953592cbdcf8b6415ad7bd3fea855e16b",
        "size_bytes": 2_276,
    },
    "challenger": {
        "path": "src/bctc_ai/mapping/e0040_calibration_challenger.py",
        "sha256": "c379ccf784868ec5b2f40714be00c402147b2b9a94e06b917a3e2cd6b926609b",
        "size_bytes": 47_333,
    },
    "formal_integration": {
        "path": "src/bctc_ai/evaluation/e0040_formal_mapping.py",
        "sha256": "3b181a409ffb5e8a1299890f5e8044bcf35bbb3cb221da091e0edb65f19f7eb8",
        "size_bytes": 105_326,
    },
    "mapper": {
        "path": "src/bctc_ai/mapping/ordered_subgraph_v2.py",
        "sha256": "cf737243cbcecf919a2cf2012aa269655341b5c8c6b8c4038c76ed510a68b40a",
        "size_bytes": 81_923,
    },
    "seal_script": {
        "path": "scripts/experiments/capture_e0040_mbb_cdkt_formal_mapping_seal.py",
        "sha256": "e3ce1d7767011d0ea1d8fa464d475e5345abcb905e9ecefc130ebdc5865b353b",
        "size_bytes": 1_737,
    },
    "text_normalization": {
        "path": "src/bctc_ai/core/text.py",
        "sha256": "2a97e6626fa6f747ff0f8e9de827b02f50dcd9a0c8e058937cd221acf1420af6",
        "size_bytes": 5_947,
    },
}

METRICS = {
    "all_intervals_exhaustive": True,
    "all_pruning_counts_zero": True,
    "base_collision_pair_count": 6,
    "baseline_interval_count": 43,
    "baseline_selected_count": 59,
    "final_interval_count": 44,
    "final_row_status_counts": {
        "NO_ADMISSIBLE_PAIR": 3,
        "RESOLVED_ANCHOR": 43,
        "RESOLVED_PATH": 18,
    },
    "final_selected_count": 61,
    "internal_role_repair_selected_count": 2,
    "mapper_invocation_count": 2,
    "new_collision_pair_count": 0,
    "normalization_changed_schema_node_count": 21,
    "normalization_derived_key_count": 33,
    "result_collision_pair_count": 6,
    "schema_node_count": 77,
    "selected_anchor_count": 43,
    "selected_path_count": 18,
    "source_only_structural_count": 3,
    "source_row_count": 64,
}
RESULT_RECEIPTS = {
    "baseline_selected_pairs_sha256": (
        "77167590e57381f8d724c713b4814e1fb2b64656643fad1f0d54dcc60f2eb416"
    ),
    "challenger_result_sha256": (
        "2e49d8623692fde9fd4a5a87f9c2e2159941b0f3ded7b7b16dddac2ab1e85fbd"
    ),
    "challenger_result_size_bytes": 700_869,
    "collision_audit_sha256": ("f00504266416e99c574ed3f93204735eeec36c39f4c416c54073dfada21ce97a"),
    "final_result_sha256": "15edfc7e349a48cec62fd5bad4bcfc506dcf2c8272055620135b2cfe6d91a29d",
    "final_result_size_bytes": 347_961,
    "final_selected_pairs_sha256": (
        "066c2c3352d65c067e7048ef55b46e6e990c3ad6a5aed94c2a1011eaba002c75"
    ),
    "final_selected_pairs_size_bytes": 2_014,
    "normalization_sha256": "09175c45fa93b4172c1f2fe1742b93a49aab3498119a451c4126f1be30b36088",
}

MAPPING_ACCESS = {
    "e0037_mapping_semantic_decode_count": 1,
    "e0037_mapping_stable_identity_read_count_per_build": 2,
    "e0037_seal_validated_before_mapping_open": True,
    "e0037_source_structure_file_opened": False,
    "e0038_or_e0039_mapping_artifact_opened": False,
    "history_or_mongodb_opened": False,
    "holdout_opened": False,
    "numeric_status_or_postjoin_artifact_opened": False,
    "period_unit_or_source_scope_answer_artifact_opened": False,
    "prior_mapping_page_and_row_ordinal_fields_passed_to_core": False,
    "process_contamination_guard_passed": True,
    "qwen_raw_rejected_or_token_output_opened": False,
    "raw_source_report_scope_extracted_or_used": False,
    "review_or_steward_answers_opened": False,
    "schema_node_applicability_scopes_present": True,
    "stable_inputs_revalidated_after_mapping": True,
    "unique_s3_restore_record_validated_before_mapping_open": True,
    "validation_order": [
        "CONTROL_IMPLEMENTATION_POLICY_RUNTIME",
        "E0037_MAPPING_SEAL",
        "S3_UNIQUE_RESTORE_RECORD",
        "E0037_MAPPING_ONLY_BYTES",
        "SCRUBBED_SOURCE_AND_BASE_PROJECTION",
        "E0040_CHALLENGER",
    ],
}
SEAL_ACCESS = {
    "answer_free_process_guarded_before_reads_and_publication": True,
    "e0038_or_e0039_mapping_artifact_opened": False,
    "history_or_mongodb_opened": False,
    "holdout_opened": False,
    "mapping_directory_exact_inventory_validated_before_replay_and_publication": True,
    "mapping_only_envelope_and_canonical_bytes_validated_before_replay": True,
    "mapping_only_stable_identity_read_count": 2,
    "numeric_status_or_postjoin_artifact_opened": False,
    "period_unit_or_source_scope_answer_artifact_opened": False,
    "qwen_raw_rejected_or_token_output_opened": False,
    "review_or_steward_answers_opened": False,
}


def _read_exact(project_root: Path, record: dict[str, object]) -> bytes:
    payload = (project_root / str(record["path"])).read_bytes()
    assert len(payload) == record["size_bytes"]
    assert hashlib.sha256(payload).hexdigest() == record["sha256"]
    return payload


def _reject_constant(value: str) -> None:
    raise AssertionError(f"non-finite JSON constant: {value}")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        assert key not in result, f"duplicate JSON key: {key}"
        result[key] = value
    return result


def _decode(payload: bytes) -> dict[str, Any]:
    result = json.loads(
        payload,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )
    assert type(result) is dict
    return result


def _pretty(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def _compact(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()


def _receipt(payload: object) -> tuple[str, int]:
    encoded = _compact(payload)
    return hashlib.sha256(encoded).hexdigest(), len(encoded)


def _named_values(payload: object, key_fragment: str) -> list[object]:
    result: list[object] = []
    if type(payload) is dict:
        for key, value in payload.items():
            if key_fragment in key:
                result.append(value)
            result.extend(_named_values(value, key_fragment))
    elif type(payload) is list:
        for value in payload:
            result.extend(_named_values(value, key_fragment))
    return result


def test_e0040_formal_artifacts_are_exact_canonical_and_linked(project_root: Path):
    mapping_bytes = _read_exact(project_root, MAPPING)
    seal_bytes = _read_exact(project_root, SEAL)
    mapping = _decode(mapping_bytes)
    seal = _decode(seal_bytes)

    assert mapping_bytes == _pretty(mapping)
    assert seal_bytes == _pretty(seal)
    assert list(mapping) == [
        "access_contract",
        "authority",
        "capture_git_commit",
        "capture_git_dirty",
        "challenger_result",
        "claim_boundary",
        "dataset_role",
        "e0037_authority_receipt",
        "experiment_id",
        "format_version",
        "implementation_hash_ledger",
        "input_hash_ledger",
        "limitations",
        "metrics",
        "result_receipts",
        "runtime_hash_ledger",
        "runtime_versions",
        "source_evidence_receipt",
        "state",
    ]
    assert list(seal) == [
        "access_contract",
        "authority",
        "claim_boundary",
        "dataset_role",
        "experiment_id",
        "format_version",
        "input_hash_ledger",
        "inventory",
        "mapping_capture_git_commit",
        "mapping_status",
        "metrics",
        "replay",
        "result_projection_sha256",
        "result_receipts",
        "seal_git_commit",
        "seal_git_dirty",
        "state",
    ]
    assert set(mapping["challenger_result"]) == {
        "baseline_result",
        "baseline_selected_pairs",
        "collision_audit",
        "combined_parent_overrides",
        "final_result",
        "final_selected_pairs",
        "mapper_invocation_count",
        "mapper_policy_sha256",
        "newly_selected_pairs",
        "normalization",
        "policy_sha256",
        "source_only_structural_rows",
    }

    assert mapping["capture_git_commit"] == CAPTURE_COMMIT
    assert mapping["capture_git_dirty"] is False
    assert (mapping["experiment_id"], mapping["dataset_role"], mapping["format_version"]) == (
        "E-0040",
        "CALIBRATION",
        1,
    )
    assert mapping["state"] == "E0040_GENERIC_CHALLENGER_MAPPING_ONLY_READY_FOR_HASH_SEAL"
    assert seal["mapping_capture_git_commit"] == CAPTURE_COMMIT
    assert seal["seal_git_commit"] == CAPTURE_COMMIT
    assert seal["seal_git_dirty"] is False
    assert (seal["experiment_id"], seal["dataset_role"], seal["format_version"]) == (
        "E-0040",
        "CALIBRATION",
        1,
    )
    assert seal["mapping_status"] == "CHALLENGER_COMPLETE_61_SELECTED_3_SOURCE_ONLY"
    assert seal["state"] == "E0040_GENERIC_CHALLENGER_MAPPING_HASH_SEALED"
    assert mapping["input_hash_ledger"]["control"] == CONTROL
    assert mapping["implementation_hash_ledger"] == IMPLEMENTATION

    seal_ledger = seal["input_hash_ledger"]
    assert seal_ledger == {
        "control": CONTROL,
        "deterministic_replay_implementation": IMPLEMENTATION,
        "deterministic_replay_inputs": mapping["input_hash_ledger"],
        "deterministic_replay_runtime": mapping["runtime_hash_ledger"],
        "deterministic_replay_runtime_versions": mapping["runtime_versions"],
        "mapping_only": MAPPING,
    }
    for ledger in (
        mapping["input_hash_ledger"],
        mapping["implementation_hash_ledger"],
        mapping["runtime_hash_ledger"],
    ):
        for record in ledger.values():
            _read_exact(project_root, record)

    mapping_path = project_root / MAPPING["path"]
    assert sorted(item.name for item in mapping_path.parent.iterdir()) == ["mapping_only.json"]
    assert not mapping_path.is_symlink()
    assert seal["inventory"] == {"file_count": 1, "files": [MAPPING]}
    assert mapping["access_contract"] == MAPPING_ACCESS
    assert seal["access_contract"] == SEAL_ACCESS
    assert mapping["authority"] == {
        "accounting_or_excel": False,
        "generic_normalization_and_role_repair_diagnostics": True,
        "holdout_or_production": False,
        "mapping_accuracy": False,
        "mapping_output_hash_identity": True,
        "numeric_period_unit_scope": False,
        "review_or_steward_approval": False,
        "schema_authority": False,
    }
    assert seal["authority"] == {
        "accounting_excel_holdout_or_production": False,
        "deterministic_replay_byte_identity": True,
        "exact_one_file_hash_identity": True,
        "mapping_accuracy": False,
        "numeric_period_unit_scope": False,
        "review_or_steward_approval": False,
        "schema_authority": False,
    }
    assert seal["replay"] == {
        "deterministic_replay_invocation_count": 1,
        "exact_canonical_byte_equality": True,
        "exact_object_equality": True,
        "mapping_and_seal_clean_git_commit_equal": True,
        "mapping_core_result_used_to_change_published_mapping": False,
        "tracked_ledger_head_blob_binding_required": True,
    }

    authority = mapping["e0037_authority_receipt"]
    registry_record = mapping["input_hash_ledger"]["s3_snapshot_registry"]
    registry_line = _read_exact(project_root, registry_record).splitlines(keepends=True)[4]
    canonical_record = _compact(_decode(registry_line))
    assert authority == {
        "manifest_sha256": ("b7b2b5bd4249d93fc8bca2210228ffd000eb36e5ebc0bb7167dde4e774478c8c"),
        "mapping_capture_git_commit": "3dd2681133e939671f9c1818656804a7753fde8a",
        "mapping_only_sha256": mapping["input_hash_ledger"]["e0037_mapping_only"]["sha256"],
        "mapping_seal_sha256": mapping["input_hash_ledger"]["e0037_mapping_seal"]["sha256"],
        "restore_verified": True,
        "run_record_sha256": ("68b35baa1f3993021db5e550b87bd42af515076dd84e2e968248a27d02a22a34"),
        "s3_registry_line": {
            "canonical_record_sha256": hashlib.sha256(canonical_record).hexdigest(),
            "line_number": 5,
            "line_sha256": hashlib.sha256(registry_line).hexdigest(),
            "line_size_bytes": len(registry_line),
            "registry_path": registry_record["path"],
        },
        "s3_snapshot_id": "20260807T170440Z-e0037-source-and-mapping-seal-e18f6b20825f",
        "s3_snapshot_record_sha256": hashlib.sha256(canonical_record).hexdigest(),
    }


def test_e0040_formal_metrics_and_result_receipts_recompute(project_root: Path):
    mapping = _decode(_read_exact(project_root, MAPPING))
    seal = _decode(_read_exact(project_root, SEAL))
    challenger = mapping["challenger_result"]
    baseline = challenger["baseline_result"]
    final = challenger["final_result"]

    assert mapping["metrics"] == seal["metrics"] == METRICS
    assert mapping["result_receipts"] == seal["result_receipts"] == RESULT_RECEIPTS
    baseline_pairs = [
        [row["row_id"], row["selected_report_norm_id"]]
        for row in baseline["row_mappings"]
        if row["selected_report_norm_id"] is not None
    ]
    final_pairs = [
        [row["row_id"], row["selected_report_norm_id"]]
        for row in final["row_mappings"]
        if row["selected_report_norm_id"] is not None
    ]
    assert baseline_pairs == challenger["baseline_selected_pairs"]
    assert final_pairs == challenger["final_selected_pairs"]
    assert (len(baseline_pairs), len(final_pairs)) == (59, 61)
    assert len(set(map(tuple, baseline_pairs))) == 59
    assert len(set(map(tuple, final_pairs))) == 61
    new_pairs = set(map(tuple, final_pairs)) - set(map(tuple, baseline_pairs))
    assert new_pairs == set(map(tuple, challenger["newly_selected_pairs"]))
    assert len(new_pairs) == 2
    assert {
        (item["row_id"], item["target_report_norm_id"])
        for item in challenger["combined_parent_overrides"]
    } == new_pairs

    assert Counter(row["status"] for row in final["row_mappings"]) == {
        "NO_ADMISSIBLE_PAIR": 3,
        "RESOLVED_ANCHOR": 43,
        "RESOLVED_PATH": 18,
    }
    source_only = challenger["source_only_structural_rows"]
    assert len(source_only) == 3
    assert all(item["selected_report_norm_id"] is None for item in source_only)
    assert {item["row_id"] for item in source_only} == {
        row["row_id"] for row in final["row_mappings"] if row["status"] == "NO_ADMISSIBLE_PAIR"
    }
    assert len(baseline["intervals"]) == baseline["search"]["intervals"] == 43
    assert len(final["intervals"]) == final["search"]["intervals"] == 44
    assert _named_values(baseline, "search_exhaustive") == [True] * 43
    assert _named_values(final, "search_exhaustive") == [True] * 44
    assert set(_named_values(baseline, "prun")) == {0}
    assert set(_named_values(final, "prun")) == {0}

    collision = challenger["collision_audit"]
    assert collision["node_count"] == 77
    assert len(collision["base_collision_pairs"]) == 6
    assert collision["result_collision_pairs"] == collision["base_collision_pairs"]
    assert collision["new_collision_pairs"] == []
    assert (
        len(
            {
                (item["semantic_key"], item["left_report_norm_id"], item["right_report_norm_id"])
                for item in collision["result_collision_pairs"]
            }
        )
        == 6
    )
    normalization = challenger["normalization"]
    assert (normalization["changed_schema_node_count"], normalization["derived_key_count"]) == (
        21,
        33,
    )
    assert normalization["id_scoped_alias_invocation_count"] == 0
    assert normalization["bank_page_or_row_rule_invocation_count"] == 0

    assert _receipt(baseline_pairs)[0] == RESULT_RECEIPTS["baseline_selected_pairs_sha256"]
    assert _receipt(final_pairs) == (
        RESULT_RECEIPTS["final_selected_pairs_sha256"],
        RESULT_RECEIPTS["final_selected_pairs_size_bytes"],
    )
    assert _receipt(final) == (
        RESULT_RECEIPTS["final_result_sha256"],
        RESULT_RECEIPTS["final_result_size_bytes"],
    )
    assert _receipt(challenger) == (
        RESULT_RECEIPTS["challenger_result_sha256"],
        RESULT_RECEIPTS["challenger_result_size_bytes"],
    )
    assert _receipt(collision)[0] == RESULT_RECEIPTS["collision_audit_sha256"]
    assert _receipt(normalization)[0] == RESULT_RECEIPTS["normalization_sha256"]

    source_receipt = mapping["source_evidence_receipt"]
    source_ids = [row["row_id"] for row in final["row_mappings"]]
    schema_ids = [item["report_norm_id"] for item in final["schema_dispositions"]]
    assert len(source_ids) == len(set(source_ids)) == 64
    assert len(schema_ids) == len(set(schema_ids)) == 77
    assert _receipt(source_ids)[0] == source_receipt["source_row_ids_sha256"]
    assert _receipt(schema_ids)[0] == source_receipt["schema_report_norm_ids_sha256"]

    result_projection = "5c3c4a09650beda8eca21e5a00fe459e052ae7cc8d735359bc41a58a391da9b0"
    assert normalization["result_projection_sha256"] == result_projection
    assert baseline["schema_projection_sha256"] == result_projection
    assert final["schema_projection_sha256"] == result_projection
    assert seal["result_projection_sha256"] == result_projection


def test_e0040_formal_mapping_replays_exactly_in_a_fresh_process(project_root: Path):
    replay = r"""
import hashlib
import json
import sys
from pathlib import Path
from bctc_ai.evaluation.e0040_formal_mapping import build_e0040_mapping_only

root = Path(sys.argv[1]).resolve()
captured_bytes = Path(sys.argv[2]).read_bytes()
captured = json.loads(captured_bytes)
replayed = build_e0040_mapping_only(root, capture_git_commit=captured["capture_git_commit"])
replayed_bytes = (json.dumps(replayed, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
assert captured == replayed
assert captured_bytes == replayed_bytes
print(json.dumps({"sha256": hashlib.sha256(replayed_bytes).hexdigest(), "size": len(replayed_bytes)}))
"""
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "947"
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            replay,
            str(project_root),
            str(project_root / MAPPING["path"]),
        ],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == {
        "sha256": MAPPING["sha256"],
        "size": MAPPING["size_bytes"],
    }
