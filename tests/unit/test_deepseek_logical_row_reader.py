from __future__ import annotations

import pytest

from bctc_ai.ocr import deepseek_logical_row_reader
from bctc_ai.ocr.deepseek_logical_row_reader import (
    DeepSeekLogicalRowReaderError,
    load_deepseek_logical_row_config,
)


def test_deepseek_logical_row_config_is_rtx4090_reference_blind(project_root):
    config, base, path = load_deepseek_logical_row_config(
        project_root,
        project_root / "config/models/deepseek-ocr2-line-rtx4090-v3.toml",
    )

    assert path.is_file()
    assert base["model"]["repo_id"] == "deepseek-ai/DeepSeek-OCR-2"
    assert config["runtime_compatibility"]["minimum_compute_capability"] == [8, 9]
    assert config["runtime_compatibility"]["historical_blackwell_runtime_claimed"] is False
    assert config["inference"]["reference_text_available_to_decoder"] is False
    assert all(value is False for value in config["safety"].values())


def test_deepseek_logical_row_config_rejects_template_access(monkeypatch, project_root):
    source = project_root / "config/models/deepseek-ocr2-line-rtx4090-v3.toml"
    original_load_toml = deepseek_logical_row_reader._load_toml

    def load_with_drift(path, name):
        payload = original_load_toml(path, name)
        if name == "DeepSeek logical-row config":
            payload["safety"]["template_access"] = True
        return payload

    monkeypatch.setattr(deepseek_logical_row_reader, "_load_toml", load_with_drift)

    with pytest.raises(DeepSeekLogicalRowReaderError, match="configuration drifted"):
        load_deepseek_logical_row_config(project_root, source)
