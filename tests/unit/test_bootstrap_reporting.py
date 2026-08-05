from __future__ import annotations

from bctc_ai.reporting.bootstrap import _write_dynamic_audits


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
