from __future__ import annotations

import pytest

from bctc_ai.evaluation.holdout_freeze import HoldoutFreezeError, validate_holdout_freeze


def test_e0022_freeze_is_preinspection_and_sources_are_absent(project_root):
    result = validate_holdout_freeze(
        project_root,
        project_root / "config/experiments/e0022-acb-q1-2026-untouched-holdout.yaml",
        require_sources_absent=True,
    )

    assert result.dataset_role == "UNTOUCHED_HOLDOUT"
    assert result.frozen_git_commit == "e0496e2196ada0a66213469d09296528dd37cc54"
    assert result.frozen_file_count == 24
    assert len(result.sources) == 2
    assert all(source.locally_present is False for source in result.sources)
    assert result.schema_item_count == 1593
    assert result.tm_1944_present is True
    assert result.role_a_access_gate == "FORBIDDEN_UNTIL_ROLE_B_SEALED"
    assert result.thresholds_reusable_for_retuning is False


def test_e0022_freeze_rejects_source_access_before_seal(project_root, monkeypatch):
    original_is_file = type(project_root).is_file

    def pretend_role_a_is_present(path):
        if path.name == "ACB BCTC HOP NHAT Q1_26_ban tra cuu.pdf":
            return True
        return original_is_file(path)

    monkeypatch.setattr(type(project_root), "is_file", pretend_role_a_is_present)

    with pytest.raises(HoldoutFreezeError, match="accessed before pre-access seal"):
        validate_holdout_freeze(
            project_root,
            project_root / "config/experiments/e0022-acb-q1-2026-untouched-holdout.yaml",
            require_sources_absent=True,
        )
