from __future__ import annotations

import json

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.recovery.artifact_registry import (
    RecoveryArtifactError,
    verify_frozen_artifact,
)


def test_current_lost_batch_resolves_only_through_explicit_recovery(project_root):
    result = verify_frozen_artifact(
        project_root,
        {
            "path": "output/calibration/e0027-mbb-q1-2026-end-to-end-role-c/batch_manifest.json",
            "sha256": "0d94762ba4a0d383793fe93a56e48fa7b79d6a3f7faaf62e9dcf40935b8c2889",
        },
    )

    assert result.status == "FUNCTIONAL_RECOVERY_SEAL_VERIFIED_ORIGINAL_BYTES_ABSENT"
    assert result.recovery_id == "R-0001"
    assert result.recovery_seal_path == (
        "docs/recovery/R-0001-e0027-functional-reproduction.json"
    )


def test_direct_file_wins_and_wrong_missing_hash_cannot_use_recovery(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    direct = project / "direct.json"
    direct.write_text("{}\n", encoding="utf-8")
    result = verify_frozen_artifact(
        project,
        {"path": "direct.json", "sha256": sha256_file(direct)},
        registry_path=tmp_path / "unused.json",
    )
    assert result.status == "DIRECT_BYTES_VERIFIED"

    registry = project / "registry.json"
    registry.write_text(
        json.dumps(
            {
                "format_version": 1,
                "policy": "EXPLICIT_LOST_ARTIFACT_FUNCTIONAL_REPRODUCTION_V1",
                "records": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecoveryArtifactError, match="no unique registered recovery"):
        verify_frozen_artifact(
            project,
            {"path": "missing.json", "sha256": "f" * 64},
            registry_path=registry.relative_to(project),
        )
