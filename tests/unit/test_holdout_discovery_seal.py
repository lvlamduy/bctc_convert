from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.evaluation import holdout_discovery_seal
from bctc_ai.evaluation.holdout_discovery_seal import (
    HoldoutDiscoverySealError,
    capture_e0022_unresolved_role_b_discovery,
)


def test_unresolved_role_b_seal_rejects_dirty_worktree(project_root, monkeypatch):
    monkeypatch.setattr(holdout_discovery_seal, "_git", lambda *_args: " M file")

    with pytest.raises(HoldoutDiscoverySealError, match="requires a clean worktree"):
        capture_e0022_unresolved_role_b_discovery(
            project_root,
            model_cache_root=Path("/unused"),
            output_path=Path("docs/experiments/unused-e0022-seal.json"),
        )


def test_unresolved_role_b_seal_rejects_external_output(project_root, tmp_path, monkeypatch):
    monkeypatch.setattr(holdout_discovery_seal, "_git", lambda *_args: "")

    with pytest.raises(HoldoutDiscoverySealError, match="must remain in docs/experiments"):
        capture_e0022_unresolved_role_b_discovery(
            project_root,
            model_cache_root=Path("/unused"),
            output_path=tmp_path / "outside.json",
        )


def test_unresolved_role_b_seal_refuses_overwrite(project_root, monkeypatch):
    monkeypatch.setattr(holdout_discovery_seal, "_git", lambda *_args: "")

    with pytest.raises(HoldoutDiscoverySealError, match="refusing to overwrite"):
        capture_e0022_unresolved_role_b_discovery(
            project_root,
            model_cache_root=Path("/unused"),
            output_path=Path("docs/experiments/E-0022-role-b-execution-control.json"),
        )
