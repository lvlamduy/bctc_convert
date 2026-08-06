from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file
from bctc_ai.reporting.bootstrap import (
    _load_batch_mechanism_summary,
    _load_calibration_summary,
    _load_geometry_recovery_summary,
    _load_statement_location_summary,
    _write_dynamic_audits,
)


def test_calibration_summary_verifies_tracked_inputs_and_local_seals(tmp_path):
    artifact_path = tmp_path / "docs/experiments/E-0010-tcb-cross-reader-calibration.json"
    algorithm_path = tmp_path / "src/algorithm.py"
    config_path = tmp_path / "config/suite.yaml"
    seal_path = tmp_path / "output/role-a-seal.json"
    for path, content in (
        (algorithm_path, "algorithm-v1"),
        (config_path, "suite-v1"),
        (seal_path, "seal-v1"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "format_version": 2,
                "experiment_id": "E-0010",
                "dataset_role": "CALIBRATION",
                "status": "PASS_CALIBRATION_WITH_REQUIRED_ESCALATIONS",
                "code": {"git_commit": "abc", "git_dirty": False},
                "algorithm_files_sha256": {"src/algorithm.py": sha256_file(algorithm_path)},
                "suite_config": {
                    "path": "config/suite.yaml",
                    "sha256": sha256_file(config_path),
                },
                "sealed_inputs": {
                    "role_a_seal": {
                        "path": "output/role-a-seal.json",
                        "sha256": sha256_file(seal_path),
                    }
                },
                "metrics": {"strict_exact_reference_cell_agreement_rate": 0.9},
                "acceptance": {"auto_verified_high": 0},
                "off_balance_gate": {"eligible_rows_on_off_balance_pages": 0},
                "cash_flow": {"method": "DIRECT"},
                "continuation": [{"accepted": True}],
                "historical_weak_reference": {"invoked": False},
                "claim_boundary": "machine reference only",
            }
        ),
        encoding="utf-8",
    )

    passed = _load_calibration_summary(tmp_path)

    assert passed["integrity_status"] == "PASS_TRACKED_AND_LOCAL_SEALS"
    assert passed["local_seal_count"] == 1
    assert passed["verified_local_seal_count"] == 1
    algorithm_path.write_text("algorithm-drift", encoding="utf-8")
    failed = _load_calibration_summary(tmp_path)
    assert failed["integrity_status"] == "FAIL"
    assert failed["errors"] == ["algorithm hash drift: src/algorithm.py"]


def test_geometry_recovery_summary_locks_targeted_gates_and_three_seals(tmp_path):
    artifact_path = tmp_path / "docs/experiments/E-0011-tcb-geometry-recovery.json"
    algorithm_path = tmp_path / "src/geometry.py"
    experiment_path = tmp_path / "config/experiment.yaml"
    suite_path = tmp_path / "config/suite.yaml"
    reconstruction_path = tmp_path / "config/reconstruction.yaml"
    seal_paths = [tmp_path / f"output/role-{role}-seal.json" for role in "abc"]
    for path, content in (
        (algorithm_path, "geometry-v1"),
        (experiment_path, "experiment-v1"),
        (suite_path, "suite-v1"),
        (reconstruction_path, "reconstruction-v1"),
        *((path, f"seal-{index}") for index, path in enumerate(seal_paths)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    configured = {"required_alignment_actions": {"MATCH": 140}}
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "experiment_id": "E-0011",
                "dataset_role": "CALIBRATION",
                "design": "TARGETED_POST_FAILURE_ANALYSIS",
                "content_inspected_before_design": True,
                "status": "PASS_TARGETED_GEOMETRY_RECOVERY_CALIBRATION",
                "code": {"git_commit": "abc", "git_dirty": False},
                "algorithm_files_sha256": {"src/geometry.py": sha256_file(algorithm_path)},
                "experiment_config": {
                    "path": "config/experiment.yaml",
                    "sha256": sha256_file(experiment_path),
                },
                "suite_config": {
                    "path": "config/suite.yaml",
                    "sha256": sha256_file(suite_path),
                },
                "reconstruction_config": {
                    "path": "config/reconstruction.yaml",
                    "sha256": sha256_file(reconstruction_path),
                },
                "sealed_inputs": {
                    f"role_{role}_seal": {
                        "path": f"output/role-{role}-seal.json",
                        "sha256": sha256_file(path),
                    }
                    for role, path in zip("abc", seal_paths, strict=True)
                },
                "metrics": {
                    "reference_financial_row_coverage_rate": 1.0,
                    "strict_exact_reference_financial_row_agreement_rate": 1.0,
                    "reference_financial_cell_coverage_rate": 1.0,
                    "strict_exact_reference_cell_agreement_rate": 1.0,
                    "candidate_invalid_cells": 0,
                    "exact_note_references": 50,
                },
                "acceptance": {
                    "auto_verified_high": 0,
                    "configured": configured,
                    "observed": configured,
                },
                "off_balance_gate": {"eligible_rows_on_off_balance_pages": 0},
                "arithmetic_validation": {
                    "value_generation_or_overwrite": False,
                    "counts": {"PASS": 11, "NOT_TESTABLE": 1},
                },
                "cash_flow": {"schema_branch_assignment_permitted": False},
                "continuation": [{"accepted": True}],
                "recovery_evidence": {
                    "pixel_dash_recoveries": [{}, {}, {}],
                    "ocr_dash_alias_recoveries": [{}],
                    "trailing_context_rows_preserved_but_mapping_ineligible": 14,
                    "automatic_confidence_effect": "NONE",
                },
                "historical_weak_reference": {"invoked": False},
                "report_norm_id": {"ids_proposed_or_added": 0},
                "claim_boundary": "targeted calibration only",
            }
        ),
        encoding="utf-8",
    )

    passed = _load_geometry_recovery_summary(tmp_path)

    assert passed["integrity_status"] == "PASS_TRACKED_AND_LOCAL_SEALS"
    assert passed["local_seal_count"] == 3
    assert passed["verified_local_seal_count"] == 3
    reconstruction_path.write_text("reconstruction-drift", encoding="utf-8")
    failed = _load_geometry_recovery_summary(tmp_path)
    assert failed["integrity_status"] == "FAIL"
    assert failed["errors"] == ["E-0011 reconstruction_config hash drift"]


def test_batch_mechanism_summary_locks_equivalence_resume_and_seal(tmp_path):
    artifact_path = tmp_path / "docs/experiments/E-0012-ppocrv6-batch-mechanism.json"
    paths = {
        "algorithm": tmp_path / "src/batch.py",
        "config": tmp_path / "config/ocr.yaml",
        "runtime": tmp_path / "config/runtime.toml",
        "freeze": tmp_path / "config/freeze.txt",
        "source": tmp_path / "source.pdf",
        "input": tmp_path / "output/upstream/manifest.json",
        "role_b": tmp_path / "output/upstream/role_b.json",
        "render": tmp_path / "output/upstream/page.png",
        "page_manifest": tmp_path / "output/batch/page/run_manifest.json",
        "result": tmp_path / "output/batch/page/ocr_result.json",
        "seal": tmp_path / "output/batch/seal.json",
        "baseline": tmp_path / "output/baseline/ocr_result.json",
        "batch_manifest": tmp_path / "output/batch/batch_manifest.json",
    }
    for name, path in paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{name}-v1", encoding="utf-8")
    artifact_path.parent.mkdir(parents=True, exist_ok=True)

    def identity(name: str) -> dict[str, str]:
        path = paths[name]
        return {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": sha256_file(path),
        }

    result_digest = sha256_file(paths["result"])
    paths["baseline"].write_text(paths["result"].read_text(encoding="utf-8"), encoding="utf-8")
    artifact_path.write_text(
        json.dumps(
            {
                "format_version": 1,
                "experiment_id": "E-0012",
                "dataset_role": "CALIBRATION",
                "design": "CLEAN_COMMIT_BATCH_MECHANISM_REGRESSION",
                "status": "PASS_BATCH_EQUIVALENCE_RESUME_AND_SEAL",
                "code": {"git_commit": "abc", "git_dirty": False},
                "algorithm_files_sha256": {
                    identity("algorithm")["path"]: identity("algorithm")["sha256"]
                },
                "configuration": identity("config"),
                "runtime": {
                    "manifest": identity("runtime"),
                    "package_freeze": identity("freeze"),
                },
                "source": {**identity("source"), "render": identity("render")},
                "input_manifest": identity("input"),
                "upstream_role_b_seal": identity("role_b"),
                "batch": {
                    "path": "output/batch",
                    "manifest_sha256_after_resume": sha256_file(paths["batch_manifest"]),
                    "state": "OCR_COMPLETE",
                    "page_manifest": identity("page_manifest"),
                    "ocr_result": identity("result"),
                    "metrics": {
                        "completed_page_count": 1,
                        "line_count": 50,
                        "word_token_count": 380,
                        "model_load_session_count": 1,
                    },
                },
                "equivalence": {
                    "byte_identical": True,
                    "batch_ocr_result_sha256": result_digest,
                    "baseline_ocr_result_path": identity("baseline")["path"],
                    "baseline_ocr_result_sha256": result_digest,
                },
                "resume": {
                    "status": "PASS_ALREADY_COMPLETE",
                    "model_reloaded": False,
                    "model_load_sessions_before": 1,
                    "model_load_sessions_after": 1,
                },
                "sealing": {
                    **identity("seal"),
                    "status": "GEOMETRY_OCR_COMPLETE",
                    "batch_runner_verified": True,
                    "single_page_helper_verified": True,
                    "automatic_truth_promotion": False,
                    "automatic_schema_promotion": False,
                    "automatic_pdf_confidence_promotion": False,
                },
                "acceptance": {
                    "new_accuracy_sample": False,
                    "production_accuracy_approved": False,
                },
                "software_or_model_change": False,
                "historical_weak_reference": {"invoked": False},
                "report_norm_id": {"ids_proposed_or_added": 0},
                "ytd_derivation": {"invoked": False},
                "claim_boundary": "mechanism only",
            }
        ),
        encoding="utf-8",
    )

    passed = _load_batch_mechanism_summary(tmp_path)

    assert passed["integrity_status"] == "PASS_TRACKED_AND_LOCAL_ARTIFACTS"
    assert passed["local_artifact_count"] == 9
    assert passed["verified_local_artifact_count"] == 9
    paths["batch_manifest"].write_text("drift", encoding="utf-8")
    failed = _load_batch_mechanism_summary(tmp_path)
    assert failed["integrity_status"] == "FAIL"
    assert failed["errors"] == ["local E-0012 artifact hash drift: batch_manifest"]


def test_statement_location_summary_locks_scope_contract_and_local_outputs(tmp_path):
    artifact_path = tmp_path / "docs/experiments/E-0013-mbb-vcb-statement-location.json"
    tracked_paths = {
        "algorithm": tmp_path / "src/locator.py",
        "configuration": tmp_path / "config/locator.yaml",
        "ocr_configuration": tmp_path / "config/ocr.yaml",
        "runtime_manifest": tmp_path / "config/runtime.toml",
        "package_freeze": tmp_path / "config/freeze.txt",
    }
    for name, path in tracked_paths.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{name}-v1", encoding="utf-8")

    def identity(path):
        return {
            "path": path.relative_to(tmp_path).as_posix(),
            "sha256": sha256_file(path),
        }

    contracts = {
        "MBB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [10, 11], "KQKD": [13], "LCTT": [14, 15]},
            "excluded": [12],
            "notes": 16,
        },
        "VCB_2025_CONSOLIDATED": {
            "eligible": {"CDKT": [8, 9], "KQKD": [11, 12], "LCTT": [13, 14]},
            "excluded": [10],
            "notes": 15,
        },
    }
    documents = []
    output_paths = {}
    for key, contract in contracts.items():
        prefix = key.split("_")[0].lower()
        source_path = tmp_path / f"sources/{prefix}.pdf"
        preprocess_path = tmp_path / f"output/{prefix}/preprocess.json"
        batch_root = tmp_path / f"output/{prefix}/batch"
        batch_manifest_path = batch_root / "batch_manifest.json"
        output_path = batch_root / "statement-location.json"
        for path, content in (
            (source_path, f"{prefix}-source"),
            (preprocess_path, f"{prefix}-preprocess"),
            (batch_manifest_path, f"{prefix}-batch"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        local_output = {
            "state": "STATEMENT_LOCATION_COMPLETE",
            "code": {"commit": "clean-commit", "dirty": False},
            "result": {
                "errors": [],
                "runner_up_margin": 2.0,
                "block": {
                    "mapping_eligible_pages_by_statement_type": contract["eligible"],
                    "off_balance_excluded_pages": contract["excluded"],
                },
                "cash_flow": {
                    "method": "DIRECT",
                    "schema_branch_assignment_permitted": False,
                },
            },
        }
        output_path.write_text(json.dumps(local_output), encoding="utf-8")
        output_paths[key] = output_path
        documents.append(
            {
                "key": key,
                "source": {**identity(source_path), "dataset_role_frozen": True},
                "preprocess_manifest": {**identity(preprocess_path), "dpi": 120},
                "ocr_batch": {
                    "path": batch_root.relative_to(tmp_path).as_posix(),
                    "manifest_sha256": sha256_file(batch_manifest_path),
                    "checkpoint_state": "PARTIAL",
                    "completed_pages": 18,
                    "requested_pages": 80,
                },
                "location_output": {
                    **identity(output_path),
                    "state": "STATEMENT_LOCATION_COMPLETE",
                },
                "result": {
                    "candidate_count": 2,
                    "winner_runner_up_margin": 2.0,
                    "notes_boundary_page": contract["notes"],
                    "interstitial_pages": [],
                    "mapping_eligible_pages_by_statement_type": contract["eligible"],
                    "off_balance_excluded_pages": contract["excluded"],
                    "cash_flow": {
                        "pdf_method": "DIRECT",
                        "ordered_anchors": [{"page": 1}, {"page": 1}],
                        "indirect_sequence_complete": False,
                        "schema_branch_assignment_permitted": False,
                    },
                },
            }
        )

    artifact = {
        "format_version": 1,
        "experiment_id": "E-0013",
        "dataset_role": "CALIBRATION",
        "design": "CLEAN_MULTI_INSTITUTION_COARSE_STATEMENT_LOCATION_CALIBRATION",
        "status": "PASS_ORDERED_STATEMENT_LOCATION_AND_SCOPE_EXCLUSION",
        "code": {"git_commit": "clean-commit", "git_dirty": False},
        "algorithm_files_sha256": {
            identity(tracked_paths["algorithm"])["path"]: identity(tracked_paths["algorithm"])[
                "sha256"
            ]
        },
        "configuration": identity(tracked_paths["configuration"]),
        "upstream_reader": {
            "ocr_configuration": identity(tracked_paths["ocr_configuration"]),
            "runtime_manifest": identity(tracked_paths["runtime_manifest"]),
            "package_freeze": identity(tracked_paths["package_freeze"]),
            "automatic_truth_promotion": False,
            "automatic_schema_promotion": False,
            "automatic_pdf_confidence_promotion": False,
        },
        "documents": documents,
        "cross_document_checks": {
            "same_algorithm_and_configuration": True,
            "bank_name_or_page_rule_in_algorithm": False,
            "ordered_form_sequence_passed": True,
            "unknown_interstitial_pages": 0,
            "off_balance_pages_mapping_eligible": 0,
            "scope_crossing_continuation_links": 0,
            "direct_title_and_ordered_anchor_agreement": 2,
            "cash_flow_schema_assignment_attempts": 0,
            "historical_reference_invoked": False,
            "arithmetic_value_generation_invoked": False,
            "ytd_derivation_invoked": False,
        },
        "acceptance": {
            "cash_flow_schema_branch_assignment": "BLOCKED_BY_Q_BOOT_001",
            "row_or_schema_mapping_evaluated": False,
            "human_gold_evaluated": False,
            "production_accuracy_approved": False,
        },
        "software_or_model_change": False,
        "report_norm_id": {"ids_proposed_or_added": 0},
        "claim_boundary": "page/scope calibration only",
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    passed = _load_statement_location_summary(tmp_path)

    assert passed["integrity_status"] == "PASS_TRACKED_AND_LOCAL_ARTIFACTS"
    assert passed["document_count"] == 2
    assert passed["local_artifact_count"] == 8
    assert passed["verified_local_artifact_count"] == 8

    mbb_output = output_paths["MBB_2025_CONSOLIDATED"]
    drifted_output = json.loads(mbb_output.read_text(encoding="utf-8"))
    drifted_output["state"] = "UNRESOLVED"
    mbb_output.write_text(json.dumps(drifted_output), encoding="utf-8")
    documents[0]["location_output"]["sha256"] = sha256_file(mbb_output)
    artifact_path.write_text(json.dumps(artifact), encoding="utf-8")

    failed = _load_statement_location_summary(tmp_path)
    assert failed["integrity_status"] == "FAIL"
    assert failed["errors"] == ["local E-0013 output contract drift: MBB_2025_CONSOLIDATED"]


def test_dynamic_audits_separate_runtime_acceptance_from_model_approval(tmp_path):
    environment = {
        "captured_at": "2026-08-05T00:00:00+00:00",
        "hostname": "fixture-host",
        "os": {"PRETTY_NAME": "Fixture Linux"},
        "kernel": "fixture-kernel",
        "cpu": {"model": "fixture-cpu", "logical_count": 8},
        "memory": {"MemTotal": 16 * 1024**3, "SwapTotal": 0},
        "disk": {"total_bytes": 100 * 1024**3, "free_bytes": 50 * 1024**3},
        "gpu": {
            "reported_cuda": "13.2",
            "devices": [
                {
                    "name": "Fixture GPU",
                    "memory_total_mib": 16384,
                    "compute_capability": "12.0",
                    "driver_version": "595.80",
                }
            ],
        },
        "torch": {"available": False},
        "tools": {
            "nvcc": {"available": False},
            "python": {"version": "Python 3.11.10"},
        },
        "gpu_model_runtime": {
            "local_acceptance": "PASS",
            "declared_status": "LOGIC_DEVELOPMENT_INFERENCE_PASS_NOT_PRODUCTION_APPROVED",
            "required_native_arch": "sm_120",
            "declared_packages": {"torch": "2.12.0+cu130"},
            "smoke": {"torch_cuda_build": "13.0"},
            "freeze": {"installed_package_count": 122},
        },
    }
    manifest = {
        "git": {"branch": "fixture", "commit": "abc", "dirty": False},
        "sources": {
            "pdf_count": 2,
            "total_bytes": 100,
            "registry_hash": "source-hash",
            "inventory_stable": True,
            "inventory_attempts": 1,
        },
        "schemas": {
            "counts": {"CDKT": 77, "KQKD": 24, "LCTT": 107, "TM": 1385},
            "total_items": 1593,
            "graph_hash": "schema-hash",
            "hierarchy_reference": {"status": "PASS", "item_count": 1535},
        },
        "mongodb": {
            "dump_registry": {"restored_scope": {"document_count": 1851}},
            "historical_weak_reference": {
                "status": "PASS",
                "row_count": 112147,
                "bank_count": 27,
            },
        },
        "calibration": {
            "integrity_status": "PASS_TRACKED_AND_LOCAL_SEALS",
            "metrics": {
                "strict_exact_reference_financial_row_agreement_rate": 0.916667,
                "strict_exact_reference_cell_agreement_rate": 0.924242,
                "reference_financial_row_coverage_rate": 0.94697,
            },
            "acceptance": {"auto_verified_high": 0},
            "local_seal_count": 2,
            "verified_local_seal_count": 2,
            "errors": [],
        },
        "geometry_recovery": {
            "integrity_status": "PASS_TRACKED_AND_LOCAL_SEALS",
            "metrics": {
                "strict_exact_reference_financial_row_agreement_rate": 1.0,
                "strict_exact_reference_cell_agreement_rate": 1.0,
                "reference_financial_row_coverage_rate": 1.0,
            },
            "acceptance": {"auto_verified_high": 0},
            "local_seal_count": 3,
            "verified_local_seal_count": 3,
            "errors": [],
        },
        "batch_mechanism": {
            "integrity_status": "PASS_TRACKED_AND_LOCAL_ARTIFACTS",
            "metrics": {
                "completed_page_count": 1,
                "line_count": 50,
                "word_token_count": 380,
                "model_load_session_count": 1,
            },
            "equivalence": {"byte_identical": True},
            "local_artifact_count": 9,
            "verified_local_artifact_count": 9,
            "errors": [],
        },
        "statement_location": {
            "integrity_status": "PASS_TRACKED_AND_LOCAL_ARTIFACTS",
            "documents": [
                {
                    "key": "MBB_2025_CONSOLIDATED",
                    "eligible_pages": {
                        "CDKT": [10, 11],
                        "KQKD": [13],
                        "LCTT": [14, 15],
                    },
                    "off_balance_excluded_pages": [12],
                },
                {
                    "key": "VCB_2025_CONSOLIDATED",
                    "eligible_pages": {
                        "CDKT": [8, 9],
                        "KQKD": [11, 12],
                        "LCTT": [13, 14],
                    },
                    "off_balance_excluded_pages": [10],
                },
            ],
            "local_artifact_count": 8,
            "verified_local_artifact_count": 8,
            "errors": [],
        },
    }
    backup = {
        "restored_and_verified": True,
        "development_status": "PASS",
        "production_status": "FAIL",
        "off_machine": False,
    }

    _write_dynamic_audits(tmp_path, environment, manifest, backup, [])

    hardware = (tmp_path / "HARDWARE_AUDIT.md").read_text(encoding="utf-8")
    progress = (tmp_path / "PROGRESS_REPORT.md").read_text(encoding="utf-8")
    assert "Isolated GPU runtime: PASS" in hardware
    assert "122-package exact freeze" in hardware
    assert "production model approval remains blocked" in hardware
    assert "Largest error: no frozen end-to-end multi-institution" in progress
    assert "no approved GPU model runtime" not in progress
    assert "PASS weak-reference-only (112147 cells; 27 banks)" in progress
    assert "strict rows=91.67%" in progress
    assert "strict cells=92.42%" in progress
    assert "reference coverage=94.70%" in progress
    assert "auto-high=0" in progress
    assert "Targeted independent geometry recovery" in progress
    assert "Batch/checkpoint mechanism" in progress
    assert "Ordered statement location" in progress
    assert "MBB CDKT=[10, 11]" in progress
    assert "VCB CDKT=[8, 9]" in progress
    assert "byte-identical=True" in progress
    assert "strict rows=100.00%" in progress
    assert "strict cells=100.00%" in progress
    recovery = (tmp_path / "RECOVERY_AUDIT.md").read_text(encoding="utf-8")
    assert "2/2 locally present seals verify" in recovery
    assert "3/3 locally present seals verify" in recovery
    assert "9/9 locally present artifacts verify" in recovery
    assert "8/8 locally present source/preprocess/batch/result artifacts verify" in recovery
