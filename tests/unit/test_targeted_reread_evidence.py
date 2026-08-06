from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from bctc_ai.evaluation.targeted_reread_evidence import (
    TargetedRereadEvidenceError,
    _load_config,
    _validate_ppocrv6_result,
    seal_targeted_reread_evidence,
)


def _ppocrv6_payload() -> dict:
    return {
        "return_word_box": True,
        "model_settings": {
            "use_doc_preprocessor": False,
            "use_textline_orientation": False,
        },
        "rec_texts": ["1.234", "Khoản mục"],
        "rec_scores": [0.99, 0.95],
        "rec_boxes": [[0, 0, 10, 5], [0, 6, 20, 11]],
        "rec_polys": [
            [[0, 0], [10, 0], [10, 5], [0, 5]],
            [[0, 6], [20, 6], [20, 11], [0, 11]],
        ],
        "text_word_boxes": [[[0, 0, 10, 5]], [[0, 6, 20, 11]]],
        "text_word": [["1.234"], ["Khoản", "mục"]],
    }


def test_ppocrv6_evidence_axes_and_strict_financial_line_count_are_verified():
    assert _validate_ppocrv6_result(_ppocrv6_payload()) == (2, 3, 1)

    drifted = copy.deepcopy(_ppocrv6_payload())
    drifted["rec_scores"].pop()
    with pytest.raises(TargetedRereadEvidenceError, match="axes disagree"):
        _validate_ppocrv6_result(drifted)


def test_e0016_evidence_config_prohibits_selection_and_schema_authority(project_root):
    config = _load_config(
        project_root / "config/experiments/e0016-mbb-vcb-targeted-reread-evidence.yaml"
    )

    assert config["evaluated_variants"] == ["original"]
    assert all(value is False for value in config["safety"].values())
    assert config["expected_evidence_contract"]["report_norm_ids_proposed_or_added"] == 0
    assert config["expected_evidence_contract"]["automatic_value_replacement_count"] == 0


def test_e0016_evidence_config_rejects_variant_selection(tmp_path: Path, project_root: Path):
    source = project_root / "config/experiments/e0016-mbb-vcb-targeted-reread-evidence.yaml"
    payload = yaml.safe_load(source.read_text(encoding="utf-8"))
    payload["evaluated_variants"] = ["original", "grayscale"]
    config = tmp_path / "evidence.yaml"
    config.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(TargetedRereadEvidenceError, match="only original crops"):
        _load_config(config)


def test_e0016_evidence_sealer_refuses_dirty_git_before_reading_artifacts(tmp_path: Path):
    with pytest.raises(TargetedRereadEvidenceError, match="dirty worktree"):
        seal_targeted_reread_evidence(
            project_root=tmp_path,
            config_path=tmp_path / "missing.yaml",
            output_path=tmp_path / "evidence.json",
            git_state={"commit": "abc", "dirty": True},
        )


def test_e0016_evidence_sealer_refuses_overwrite(tmp_path: Path):
    output = tmp_path / "evidence.json"
    output.write_text("{}", encoding="utf-8")

    with pytest.raises(TargetedRereadEvidenceError, match="refusing to overwrite"):
        seal_targeted_reread_evidence(
            project_root=tmp_path,
            config_path=tmp_path / "missing.yaml",
            output_path=output,
            git_state={"commit": "abc", "dirty": False},
        )
