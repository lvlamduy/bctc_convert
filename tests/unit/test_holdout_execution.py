from __future__ import annotations

import pytest
import yaml

from bctc_ai.evaluation import holdout_execution
from bctc_ai.evaluation.holdout_execution import (
    HoldoutExecutionError,
    validate_role_b_execution_control,
)
from bctc_ai.storage.content_store import content_path


def _simulate_pre_execution_filesystem(project_root, monkeypatch):
    """Replay the frozen pre-execution filesystem after Role A was hydrated."""
    role_a_digest = "d8be301b9169577a0be2bbd8721cdaaab7cb37a32493ead0de5871bfcbc168dd"
    hidden_paths = {
        (
            project_root / "vietstock_bctc/ACB/2026/ACB BCTC HOP NHAT Q1_26_ban tra cuu.pdf"
        ).resolve(),
        content_path(project_root / "data/immutable", role_a_digest, ".pdf").resolve(),
        (project_root / "output/holdout/e0022-acb-q1-2026-role-b/a85402445a34e80dd424").resolve(),
    }
    original_exists = type(project_root).exists

    def pre_execution_exists(path):
        if path.resolve() in hidden_paths:
            return False
        return original_exists(path)

    monkeypatch.setattr(type(project_root), "exists", pre_execution_exists)


def test_e0022_role_b_execution_control_allows_only_full_document_role_b(project_root, monkeypatch):
    _simulate_pre_execution_filesystem(project_root, monkeypatch)
    result = validate_role_b_execution_control(
        project_root,
        project_root / "config/experiments/e0022-role-b-execution-control.yaml",
    )

    assert result.experiment_id == "E-0022"
    assert result.role_b_sha256 == (
        "a85402445a34e80dd4248471c2d23d4cf4b349ab2455b91db457f3e6effbdd4a"
    )
    assert result.role_b_size_bytes == 8027105
    assert result.role_b_page_count == 33
    assert result.role_b_text_layer_chars_first_five_pages == (0, 0, 0, 0, 0)
    assert result.role_a_locally_present is False
    assert result.role_a_immutable_locally_present is False
    assert result.role_a_holdout_output_count == 0
    assert result.output_root_exists is False
    assert result.execution_file_count == 11
    assert result.allowed_next_action == "PREPROCESS_ROLE_B_FULL_DOCUMENT"


def test_e0022_role_b_execution_control_rejects_role_a_access(project_root, monkeypatch):
    original_exists = type(project_root).exists

    def pretend_role_a_exists(path):
        if path.name == "ACB BCTC HOP NHAT Q1_26_ban tra cuu.pdf":
            return True
        return original_exists(path)

    monkeypatch.setattr(type(project_root), "exists", pretend_role_a_exists)
    with pytest.raises(HoldoutExecutionError, match="Role A source access is forbidden"):
        validate_role_b_execution_control(
            project_root,
            project_root / "config/experiments/e0022-role-b-execution-control.yaml",
        )


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        (
            "role_b",
            "sha256",
            "0" * 64,
            "Role B control differs from the pre-access frozen source",
        ),
        ("execution", "preprocess_dpi", 200, "Role B execution evidence policy drifted"),
    ],
)
def test_e0022_role_b_execution_control_rejects_cross_gate_drift(
    project_root,
    monkeypatch,
    section,
    key,
    value,
    message,
):
    _simulate_pre_execution_filesystem(project_root, monkeypatch)
    config_path = project_root / "config/experiments/e0022-role-b-execution-control.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload[section][key] = value
    monkeypatch.setattr(holdout_execution, "_load_yaml", lambda _path: payload)

    with pytest.raises(HoldoutExecutionError, match=message):
        validate_role_b_execution_control(project_root, config_path)
