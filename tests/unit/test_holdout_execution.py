from __future__ import annotations

import pytest
import yaml

from bctc_ai.evaluation import holdout_execution
from bctc_ai.evaluation.holdout_execution import (
    HoldoutExecutionError,
    validate_role_b_execution_control,
)


def test_e0022_role_b_execution_control_allows_only_full_document_role_b(project_root):
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
    config_path = project_root / "config/experiments/e0022-role-b-execution-control.yaml"
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload[section][key] = value
    monkeypatch.setattr(holdout_execution, "_load_yaml", lambda _path: payload)

    with pytest.raises(HoldoutExecutionError, match=message):
        validate_role_b_execution_control(project_root, config_path)
