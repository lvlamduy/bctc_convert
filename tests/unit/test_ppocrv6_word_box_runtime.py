from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_runner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/models/run_ppocrv6_word_boxes.py"
    spec = importlib.util.spec_from_file_location("ppocrv6_word_box_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner_module = _load_runner()


def test_ppocrv6_word_box_config_keeps_geometry_and_disables_implicit_transforms():
    config = yaml.safe_load(
        (PROJECT_ROOT / "config/models/pp-ocrv6-word-box.yaml").read_text(encoding="utf-8")
    )

    assert config["use_doc_preprocessor"] is False
    assert config["use_textline_orientation"] is False
    assert config["SubModules"]["TextDetection"]["model_name"] == "PP-OCRv6_medium_det"
    recognition = config["SubModules"]["TextRecognition"]
    assert recognition["model_name"] == "PP-OCRv6_medium_rec"
    assert recognition["score_thresh"] == 0.0
    assert recognition["return_word_box"] is True


def test_ppocrv6_runner_is_fail_closed_and_uses_only_pinned_local_models():
    shell_runner = (PROJECT_ROOT / "scripts/models/run_ppocrv6_word_boxes.sh").read_text(
        encoding="utf-8"
    )
    python_runner = (PROJECT_ROOT / "scripts/models/run_ppocrv6_word_boxes.py").read_text(
        encoding="utf-8"
    )

    assert "refusing to overwrite" in shell_runner
    assert "PP-OCRv6_medium_det" in shell_runner
    assert "PP-OCRv6_medium_rec" in shell_runner
    assert "BCTC_DATASET_ROLE" in shell_runner
    assert "return_word_box=True" in python_runner
    assert 'device="cpu"' in python_runner
    assert 'precision="fp32"' in python_runner
    assert "enable_mkldnn=False" in python_runner
    assert "PROCESS_SOCKET_CONNECT_DENIED" in python_runner
    assert "use_doc_orientation_classify=False" in python_runner
    assert "use_doc_unwarping=False" in python_runner
    assert "use_textline_orientation=False" in python_runner


def test_ppocrv6_payload_axis_validation_rejects_silent_box_loss():
    payload = {
        "return_word_box": True,
        "rec_texts": ["row"],
        "rec_scores": [0.9],
        "rec_polys": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
        "rec_boxes": [[0, 0, 1, 1]],
        "text_word_boxes": [],
        "text_word": [["row"]],
    }

    with pytest.raises(RuntimeError, match="line-axis lengths"):
        runner_module._validate_payload(payload)
