from __future__ import annotations

import tomllib


def test_numeric_recognizer_is_independent_pinned_and_proposal_only(project_root):
    path = project_root / "config/models/numeric-recognizer-v1.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8"))

    assert config["version"] == 1
    assert config["policy"] == "INDEPENDENT_FIXED_CELL_NUMERIC_PROPOSAL_V1"
    assert config["authority"] == "NUMERIC_CELL_PROPOSAL_ONLY"
    assert config["network_during_inference"] is False
    model = config["model"]
    assert model["repo_id"] == "PaddlePaddle/en_PP-OCRv5_mobile_rec"
    assert model["revision"] == "267c36e24c331595590fe7bd72bde2436fd286f2"
    assert model["weights_sha256"] == (
        "3ec8a97ed6cefe8568d3e2ee90bb193299b566a7661aa4fd52d224b96b59f66b"
    )
    assert model["weights_size_bytes"] == 7_772_315
    assert len(model["files"]) == 6
    assert "REPORT_NORM_ID" in config["forbidden_authority"]
    assert "ACCOUNTING_REPAIR" in config["forbidden_authority"]
