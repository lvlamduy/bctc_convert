from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path
from types import ModuleType

import pytest
import yaml

from bctc_ai.evaluation.tatr_structure import (
    TatrStructureError,
    build_query_predictions,
    cxcywh_to_clipped_xyxy,
    summarize_thresholds,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_downloader() -> ModuleType:
    path = PROJECT_ROOT / "scripts/bootstrap/download_tatr_model.py"
    spec = importlib.util.spec_from_file_location("tatr_model_downloader", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tatr_policy_keeps_structure_reader_out_of_mapping_and_value_authority():
    policy = yaml.safe_load(
        (PROJECT_ROOT / "config/models/reader-candidate-policy-v1.yaml").read_text(encoding="utf-8")
    )
    assert policy["implementation_order"][0]["candidate"] == "TATR_V1_1_ALL"
    assert policy["implementation_order"][1]["candidate"] == "DEEPSEEK_OCR_2"
    assert policy["authority"]["template_display_order_is_authoritative"] is True
    assert policy["authority"]["structure_reader_may_assign_schema_id"] is False
    assert all(value is False for value in policy["safety"].values())


def test_tatr_checkpoint_has_exact_integrity_and_safety_pins():
    config = tomllib.loads(
        (PROJECT_ROOT / "config/models/tatr-v1.1-all.toml").read_text(encoding="utf-8")
    )
    assert config["model"]["repo_id"].startswith("microsoft/")
    assert len(config["model"]["revision"]) == 40
    assert config["model"]["training_domains"] == ["PubTables-1M", "FinTabNet.c"]
    assert (
        sum(item["size_bytes"] for item in config["artifacts"].values())
        == config["required_artifact_bytes"]
    )
    assert all(len(item["sha256"]) == 64 for item in config["artifacts"].values())
    assert all(value is False for value in config["safety"].values())


def test_tatr_downloader_rejects_artifact_hash_drift(tmp_path: Path):
    downloader = _load_downloader()
    artifact = tmp_path / "model.bin"
    artifact.write_bytes(b"drift")
    config = {
        "required_artifact_bytes": len(b"drift"),
        "model": {"repo_id": "microsoft/test", "revision": "a" * 40},
        "artifacts": {
            "weights": {
                "path": artifact.name,
                "size_bytes": len(b"drift"),
                "sha256": "0" * 64,
            }
        },
    }
    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        downloader._verify_model(tmp_path, config)


def test_tatr_box_conversion_clips_to_source_image():
    normalized, pixels, status = cxcywh_to_clipped_xyxy(
        [-0.1, 0.5, 0.4, 0.5], image_width=1000, image_height=500
    )
    assert normalized == [0.0, 0.25, 0.1, 0.75]
    assert pixels == [0.0, 125.0, 100.0, 375.0]
    assert status == "VALID"


def test_tatr_retains_all_queries_and_reports_thresholds_without_values():
    predictions = build_query_predictions(
        boxes=[[0.5, 0.2, 0.8, 0.1], [0.5, 0.7, 0.8, 0.1]],
        probabilities=[[0.01, 0.90, 0.02, 0.01, 0.01, 0.01, 0.04], [0.01] * 6 + [0.94]],
        id2label={
            0: "table",
            1: "table row",
            2: "table column",
            3: "table column header",
            4: "table projected row header",
            5: "table spanning cell",
        },
        image_width=1000,
        image_height=500,
    )
    assert len(predictions) == 2
    assert set(predictions[0]) == {
        "query_index",
        "predicted_class_id",
        "predicted_label",
        "object_score",
        "no_object_score",
        "scores_by_label",
        "bbox_normalized_xyxy",
        "bbox_source_pixels_xyxy",
        "bbox_status",
    }
    summary = summarize_thresholds(predictions, [0.5, 0.95])
    assert summary["0.500000"]["counts_by_label"] == {"table row": 1}
    assert summary["0.950000"]["retained_query_count"] == 0


def test_tatr_rejects_probability_axis_without_no_object_class():
    with pytest.raises(TatrStructureError, match="including no-object"):
        build_query_predictions(
            boxes=[[0.5, 0.5, 0.2, 0.2]],
            probabilities=[[0.5, 0.5]],
            id2label={0: "table", 1: "table row"},
            image_width=100,
            image_height=100,
        )
