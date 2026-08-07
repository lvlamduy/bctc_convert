from __future__ import annotations

import tomllib

import pytest

from bctc_ai.ocr.vietocr_logical_row_reader import (
    VietOCRLogicalRowReaderError,
    load_vietocr_logical_row_config,
)


def test_vietocr_logical_row_config_is_rtx4090_reference_blind(project_root):
    path = project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    config = load_vietocr_logical_row_config(path)

    assert config["runtime_compatibility"]["minimum_compute_capability"] == [8, 9]
    assert config["runtime_compatibility"]["historical_blackwell_runtime_claimed"] is False
    assert config["inference"]["reference_text_available_to_decoder"] is False
    assert all(value is False for value in config["safety"].values())


def test_vietocr_logical_row_config_rejects_authority(tmp_path, project_root):
    source = project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    payload = tomllib.loads(source.read_text(encoding="utf-8"))
    text = source.read_text(encoding="utf-8").replace(
        "mapping_authority = false", "mapping_authority = true"
    )
    assert payload["safety"]["mapping_authority"] is False
    drifted = tmp_path / "vietocr.toml"
    drifted.write_text(text, encoding="utf-8")

    with pytest.raises(VietOCRLogicalRowReaderError, match="configuration drifted"):
        load_vietocr_logical_row_config(drifted)
