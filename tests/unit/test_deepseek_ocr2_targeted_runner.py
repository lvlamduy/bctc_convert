from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_runner() -> ModuleType:
    path = PROJECT_ROOT / "scripts/models/run_deepseek_ocr2_targeted.py"
    spec = importlib.util.spec_from_file_location("deepseek_ocr2_targeted_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_deepseek_runtime_overlay_is_hash_locked_and_non_authoritative():
    config = runner._load_config(runner.DEFAULT_CONFIG)
    overlay = config["runtime_overlay"]
    requirements = PROJECT_ROOT / overlay["requirements_path"]

    assert runner._sha256(requirements) == overlay["requirements_sha256"]
    assert overlay["flash_attention_required"] is False
    assert config["inference"]["attention_implementation"] == "eager"
    assert config["runtime_compatibility"]["packages"]["transformers"] == "4.46.3"
    assert config["runtime_compatibility"]["packages"]["torch"] == "2.12.0+cu130"
    assert all(value is False for value in config["safety"].values())


def test_deepseek_overlay_requirement_entries_are_pinned_with_hashes():
    config = tomllib.loads(runner.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    requirements = (PROJECT_ROOT / config["runtime_overlay"]["requirements_path"]).read_text(
        encoding="utf-8"
    )
    package_lines = [line for line in requirements.splitlines() if "==" in line]
    hash_lines = [line for line in requirements.splitlines() if "--hash=sha256:" in line]

    assert len(package_lines) == 11
    assert len(hash_lines) == len(package_lines)
    assert "transformers==4.46.3" in requirements
    assert "tokenizers==0.20.3" in requirements
    assert "huggingface-hub==0.26.3" in requirements


def test_layout_references_remain_explicit_non_authoritative_proposals():
    raw = (
        "<|ref|>table<|/ref|><|det|>[[10, 20, 900, 950]]<|/det|>\n"
        "<|ref|>bad<|/ref|><|det|>[[900, 10, 100, 20]]<|/det|>"
    )
    records = runner.parse_layout_references(raw)

    assert records[0]["normalized_0_999_boxes"] == [[10.0, 20.0, 900.0, 950.0]]
    assert records[0]["status"] == "PROPOSAL_ONLY"
    assert records[0]["authority"] == "NONE_GEOMETRY_PROPOSAL_ONLY"
    assert records[1]["normalized_0_999_boxes"] == []
    assert records[1]["status"] == "INVERTED_COORDINATES"
