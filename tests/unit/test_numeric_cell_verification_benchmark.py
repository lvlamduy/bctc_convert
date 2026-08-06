from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import numeric_cell_verification_benchmark
from bctc_ai.evaluation.numeric_cell_verification_benchmark import (
    NumericCellVerificationBenchmarkError,
    capture_e0031_numeric_cell_verification_benchmark,
)


def test_e0031_capture_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(
        numeric_cell_verification_benchmark, "_git", lambda *_args: " M file"
    )

    with pytest.raises(
        NumericCellVerificationBenchmarkError, match="requires clean Git code"
    ):
        capture_e0031_numeric_cell_verification_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0031-mbb-cdkt-numeric-verification.yaml"
            ),
            crop_registry_path=Path("unused"),
            reader_output_directory=Path("unused"),
            output_path=Path("docs/experiments/unused-e0031.json"),
        )


def test_e0031_capture_refuses_existing_output(project_root, monkeypatch):
    monkeypatch.setattr(numeric_cell_verification_benchmark, "_git", lambda *_args: "")

    with pytest.raises(NumericCellVerificationBenchmarkError, match="refusing to overwrite"):
        capture_e0031_numeric_cell_verification_benchmark(
            project_root,
            experiment_config_path=Path(
                "config/experiments/e0031-mbb-cdkt-numeric-verification.yaml"
            ),
            crop_registry_path=Path("unused"),
            reader_output_directory=Path("unused"),
            output_path=Path("docs/experiments/E-0026-REPLAY.md"),
        )
