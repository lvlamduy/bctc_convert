from __future__ import annotations

import json

from bctc_ai.core.hashing import sha256_file
from bctc_ai.reporting.bootstrap import (
    _load_calibration_summary,
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
                "algorithm_files_sha256": {
                    "src/algorithm.py": sha256_file(algorithm_path)
                },
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
            "counts": {"CDKT": 77, "KQKD": 24, "LCTT": 107, "TM": 1384},
            "total_items": 1592,
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
    recovery = (tmp_path / "RECOVERY_AUDIT.md").read_text(encoding="utf-8")
    assert "2/2 locally present seals verify" in recovery
