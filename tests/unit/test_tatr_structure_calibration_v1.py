from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.tatr_structure_calibration_v1 import (
    FIXED_OBJECT_SCORE_THRESHOLDS,
    TATR_ID2LABEL,
    TATR_LABELS,
    ArtifactPin,
    TatrRunPin,
    TatrStructureCalibrationError,
    _cardinality_primary_weights,
    _maximum_weight_assignment,
    _verify_clean_descendant_run_commit,
    score_tatr_structure_panel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _pin(path: Path) -> ArtifactPin:
    return ArtifactPin(path=path, sha256=sha256_file(path))


def _ref(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def _git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=input_bytes,
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8").strip()


def _commit_all(root: Path, message: str) -> str:
    _git(root, "add", "--all")
    _git(root, "commit", "--quiet", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _query(
    query_index: int,
    label: str,
    bbox: list[float],
    *,
    width: int = 100,
    height: int = 100,
    object_score: float = 0.8,
) -> dict[str, Any]:
    other = (1.0 - object_score - 0.1) / (len(TATR_LABELS) - 1)
    scores = {item: (object_score if item == label else other) for item in TATR_LABELS}
    return {
        "query_index": query_index,
        "predicted_class_id": TATR_LABELS.index(label),
        "predicted_label": label,
        "object_score": object_score,
        "no_object_score": 0.1,
        "scores_by_label": scores,
        "bbox_normalized_xyxy": [
            bbox[0] / width,
            bbox[1] / height,
            bbox[2] / width,
            bbox[3] / height,
        ],
        "bbox_source_pixels_xyxy": bbox,
        "bbox_status": "VALID",
    }


def _no_object_query(query_index: int) -> dict[str, Any]:
    scores = {item: 0.01 for item in TATR_LABELS}
    return {
        "query_index": query_index,
        "predicted_class_id": 0,
        "predicted_label": "table",
        "object_score": 0.01,
        "no_object_score": 0.94,
        "scores_by_label": scores,
        "bbox_normalized_xyxy": [0.0, 0.0, 0.01, 0.01],
        "bbox_source_pixels_xyxy": [0.0, 0.0, 1.0, 1.0],
        "bbox_status": "VALID",
    }


def _build_panel(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "TATR scorer test")
    _git(root, "config", "user.email", "tatr-scorer@example.invalid")
    (root / ".gitignore").write_text("runs/\n", encoding="utf-8")
    _git(root, "commit", "--quiet", "--allow-empty", "-m", "base")
    base_commit = _git(root, "rev-parse", "HEAD")
    for relative in (
        "config/models/tatr-v1.1-all.toml",
        "config/models/gpu-runtime.toml",
        "scripts/models/run_tatr_structure.py",
        "src/bctc_ai/evaluation/tatr_structure.py",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((PROJECT_ROOT / relative).read_bytes())
    config = tomllib.loads((root / "config/models/tatr-v1.1-all.toml").read_text(encoding="utf-8"))

    source_spec = _write_json(root / "source/source-panel.json", {"frozen": True})
    gold_input = _write_json(root / "source/source-gold-input.json", {"frozen": True})
    source_result = root / "source/result.json"
    source_render = root / "source/render.png"
    from PIL import Image

    Image.new("RGB", (120, 120), "white").save(source_render)
    _write_json(
        source_result,
        {
            "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V2",
            "input_render_ref": {
                "path": source_render.relative_to(root).as_posix(),
                "sha256": sha256_file(source_render),
                "size_bytes": source_render.stat().st_size,
            },
            "lines": [
                {"raw_pixel_bbox": [10, 20, 110, 30]},
                {"raw_pixel_bbox": [70, 45, 90, 60]},
                {"raw_pixel_bbox": [10, 60, 110, 120]},
            ],
        },
    )
    crop = root / "frozen/crops/table-0001.png"
    crop.parent.mkdir(parents=True)
    with Image.open(source_render) as render:
        render.crop((10, 20, 110, 120)).save(crop)

    manifest_commit = _commit_all(root, "freeze source inputs")

    sample = {
        "sample_id": "table-0001",
        "crop_path": crop.relative_to(root).as_posix(),
        "crop_sha256": sha256_file(crop),
        "crop_width": 100,
        "crop_height": 100,
        "source_result_ref": _ref(source_result, root),
        "source_render_ref": _ref(source_render, root),
        "source_line_indices": [0, 1, 2],
        "crop_source_bbox_raw_pixels": [10, 20, 110, 120],
        "table_source_bbox_raw_pixels": [10, 20, 110, 120],
        "selected_line_count": 3,
        "padding_pixels": 0,
    }
    manifest_path = _write_json(
        root / "frozen/crop_manifest.json",
        {
            "format_version": "MULTIBANK_TABLE_STRUCTURE_CROP_MANIFEST_V1",
            "state": "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE",
            "dataset_role": "CALIBRATION",
            "git_dirty": False,
            "git_commit": manifest_commit,
            "design_checkpoint_git_commit": manifest_commit,
            "authority": {
                "mapping_value_period_scope_semantic_authority": False,
                "structure_proposal_only": True,
            },
            "inference_firewall": {
                "bank_family_page_control_or_expected_truth_exposed_to_model": False,
                "ocr_transcript_consulted_by_crop_selector": False,
                "role_a_schema_history_or_values_consulted_by_crop_selector": False,
            },
            "sample_count": 1,
            "samples": [sample],
            "selected_source_line_count": 3,
            "source_page_count": 1,
            "source_spec_ref": _ref(source_spec, root),
        },
    )
    request_path = _write_json(
        root / "frozen/model_request.json",
        {
            "format_version": "MULTIBANK_TABLE_STRUCTURE_MODEL_REQUEST_V1",
            "state": "REFERENCE_BLIND_REQUEST_FROZEN",
            "dataset_role": "CALIBRATION",
            "evidence_role": "TABLE_STRUCTURE_PROPOSAL_ONLY",
            "git_commit": manifest_commit,
            "git_dirty": False,
            "reference_text_available_to_reader": False,
            "expected_structure_available_to_reader": False,
            "crop_manifest": {
                "path": manifest_path.relative_to(root).as_posix(),
                "sha256": sha256_file(manifest_path),
                "size_bytes": manifest_path.stat().st_size,
            },
            "sample_count": 1,
            "samples": [
                {
                    "sample_id": sample["sample_id"],
                    "category": "TABLE_STRUCTURE",
                    "crop_path": sample["crop_path"],
                    "crop_sha256": sample["crop_sha256"],
                }
            ],
        },
    )

    predictions = [
        _query(0, "table", [0.0, 0.0, 100.0, 100.0]),
        _query(1, "table column", [50.0, 0.0, 100.0, 100.0]),
        _query(2, "table row", [0.0, 20.0, 100.0, 50.0]),
        _query(3, "table column header", [0.0, 0.0, 100.0, 20.0]),
        *[_no_object_query(index) for index in range(4, 125)],
    ]
    result_path = _write_json(
        root / "runs/table-0001/structure_result.json",
        {
            "schema_version": 1,
            "model_key": "TATR_V1_1_ALL",
            "image": {"width": 100, "height": 100},
            "model_labels": TATR_ID2LABEL,
            "query_predictions": predictions,
            "threshold_summary": {"ignored": "scorer replays raw queries"},
        },
    )
    run_path = _write_json(
        root / "runs/table-0001/run_manifest.json",
        {
            "schema_version": 1,
            "state": "STRUCTURE_INFERENCE_COMPLETE",
            "dataset_role": "CALIBRATION",
            "evidence_role": "NON_GENERATIVE_TABLE_STRUCTURE_PROPOSAL_ONLY",
            "confidence_policy": "NO_AUTOMATIC_TRUTH_SCHEMA_OR_VALUE_PROMOTION",
            "input": {
                "path": crop.relative_to(root).as_posix(),
                "size_bytes": crop.stat().st_size,
                "sha256": sha256_file(crop),
                "width": 100,
                "height": 100,
            },
            "runtime": {
                "base_manifest_path": "config/models/gpu-runtime.toml",
                "base_manifest_sha256": (
                    "9141e0a4177f66f152bdb9eecbbfdbdd3add566dbabb81b43207a018c1ba18d8"
                ),
                "transformers": "5.14.1",
                "model": {
                    "repo_id": "microsoft/table-transformer-structure-recognition-v1.1-all",
                    "revision": "7587a7ef111d9dcbf8ac695f1376ab7014340a0c",
                    "license": "MIT",
                    "loaded_parameter_count": 28_828_619,
                    "loaded_state_element_count": 28_847_819,
                    "artifacts": [
                        {
                            "key": "config_json",
                            "path": (
                                "/workspace/bctc-ai-models/official_models/"
                                "table-transformer-structure-recognition-v1.1-all/config.json"
                            ),
                            "size_bytes": 76_761,
                            "sha256": (
                                "17a8a6edfb9e394263fa6ba9b82176ebccdfcc5d6cd29121ec91572c7d6be22c"
                            ),
                        },
                        {
                            "key": "preprocessor_config",
                            "path": (
                                "/workspace/bctc-ai-models/official_models/"
                                "table-transformer-structure-recognition-v1.1-all/"
                                "preprocessor_config.json"
                            ),
                            "size_bytes": 374,
                            "sha256": (
                                "eead409bb80e36ae85b8377642c54550f0504f65688ba3a4967950cafe461df2"
                            ),
                        },
                        {
                            "key": "weights",
                            "path": (
                                "/workspace/bctc-ai-models/official_models/"
                                "table-transformer-structure-recognition-v1.1-all/"
                                "model.safetensors"
                            ),
                            "size_bytes": 115_437_156,
                            "sha256": (
                                "9df416575a3a36ebd0129342d4f597f14d6e5170268f3d52d28584ab4466a501"
                            ),
                        },
                    ],
                },
            },
            "code": {"commit": manifest_commit, "dirty": False},
            "configuration": {
                "path": "config/models/tatr-v1.1-all.toml",
                "sha256": ("b0328237e4e694f1a6325d01dca914a5c832e709963beaa86ee5ba435887b9ec"),
                "runner_path": "scripts/models/run_tatr_structure.py",
                "runner_sha256": (
                    "dd920f6021f52cfe5cece49b17d60e5ebfd6702c889a55a864a7e98113014aa1"
                ),
                "checkpoint_processor_size": {"longest_edge": 800},
                "runtime_processor_size": {"shortest_edge": 800, "longest_edge": 800},
                "processor_compatibility_applied": True,
                "experimental_processor_size_override": False,
                "implicit_orientation_or_unwarp": False,
                "network_policy": "PROCESS_SOCKET_CONNECT_DENIED",
                "checkpoint_compatibility": {
                    "model_config": {
                        "mode": config["compatibility"]["mode"],
                        "field": "dilation",
                        "checkpoint_value": None,
                        "resolved_value": False,
                        "runtime_transformers": "5.14.1",
                        "checkpoint_artifact_mutated": False,
                        "reason": config["compatibility"]["reason"],
                    },
                    "image_processor": {
                        "mode": config["processor_compatibility"]["mode"],
                        "checkpoint_size": {"longest_edge": 800},
                        "resolved_size": {"shortest_edge": 800, "longest_edge": 800},
                        "runtime_transformers": "5.14.1",
                        "aspect_ratio_preserved": True,
                        "checkpoint_artifact_mutated": False,
                        "reason": config["processor_compatibility"]["reason"],
                    },
                },
            },
            "metrics": {
                "wall_seconds": 0.25,
                "peak_gpu_allocated_mib": 100.0,
                "peak_gpu_reserved_mib": 120.0,
                "query_count": len(predictions),
                "processed_tensor_shape": [1, 3, 100, 100],
            },
            "safety": config["safety"],
            "artifacts": {
                "structure_result": {
                    "path": "structure_result.json",
                    "size_bytes": result_path.stat().st_size,
                    "sha256": sha256_file(result_path),
                }
            },
        },
    )
    truth_path = _write_json(
        root / "truth.json",
        {
            "format_version": "MULTIBANK_TABLE_STRUCTURE_SOURCE_GOLD_V1",
            "state": "FROZEN_BEFORE_ANY_STRUCTURE_MODEL_INFERENCE",
            "design_checkpoint_git_commit": manifest_commit,
            "gold_input_ref": _ref(gold_input, root),
            "crop_manifest": {
                "path": manifest_path.relative_to(root).as_posix(),
                "sha256": sha256_file(manifest_path),
                "size_bytes": manifest_path.stat().st_size,
            },
            "sample_count": 1,
            "samples": [
                {
                    "sample_id": "table-0001",
                    "bank": "OPAQUE_BANK_AFTER_JOIN",
                    "control_kind": "POSITIVE",
                    "crop_ref": _ref(crop, root),
                    "expected_control_disposition": "ACCEPT",
                    "expected_structural_family_merge": True,
                    "family": "FIXTURE_FAMILY",
                    "physical_page": 1,
                    "gold_content_table_source_bbox_raw_pixels": [10, 20, 110, 120],
                    "ignored_noncontent_line_count": 0,
                    "ignored_noncontent_line_indices": [],
                    "ignored_noncontent_reason": "NONE",
                    "logical_row_count": 1,
                    "numeric_lane_count": 1,
                    "header_row_count": 1,
                    "spanning_cell_required": False,
                    "nested_row_required": False,
                    "optional_row_behavior": "NONE",
                    "class_coverage": {
                        "table": "SCORABLE_WITH_INSTANCES",
                        "table column": "SCORABLE_WITH_INSTANCES",
                        "table row": "SCORABLE_WITH_INSTANCES",
                        "table column header": "SCORABLE_WITH_INSTANCES",
                        "table projected row header": "SCORABLE_ZERO_INSTANCE",
                        "table spanning cell": "SCORABLE_ZERO_INSTANCE",
                    },
                    "gold_objects": [
                        {
                            "object_id": "table",
                            "label": "table",
                            "bbox_crop_pixels_xyxy": [0.0, 0.0, 100.0, 100.0],
                        },
                        {
                            "object_id": "numeric-column",
                            "label": "table column",
                            "bbox_crop_pixels_xyxy": [50.0, 0.0, 100.0, 100.0],
                        },
                        {
                            "object_id": "row-1",
                            "label": "table row",
                            "bbox_crop_pixels_xyxy": [0.0, 20.0, 100.0, 50.0],
                        },
                        {
                            "object_id": "header-1",
                            "label": "table column header",
                            "bbox_crop_pixels_xyxy": [0.0, 0.0, 100.0, 20.0],
                        },
                    ],
                    "value_anchors": [
                        {
                            "anchor_id": "value-1",
                            "bbox_crop_pixels_xyxy": [60.0, 25.0, 80.0, 40.0],
                            "expected_row_object_id": "row-1",
                            "expected_column_object_id": "numeric-column",
                            "logical_row_ordinal": 1,
                            "numeric_lane_ordinal": 1,
                            "source_line_index": 1,
                        }
                    ],
                    "value_cell_coverage_summary": {
                        "cell_slot_count": 1,
                        "source_anchored_value_cell_count": 1,
                        "visible_unscored_dash_cell_count": 0,
                        "other_unanchored_cell_count": 0,
                    },
                    "visible_unscored_dash_cells": [],
                }
            ],
        },
    )
    run_commit = _commit_all(root, "freeze source gold before inference")
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    run_manifest["code"]["commit"] = run_commit
    _write_json(run_path, run_manifest)
    return {
        "root": root,
        "manifest": _pin(manifest_path),
        "request": _pin(request_path),
        "truth": _pin(truth_path),
        "run": TatrRunPin(
            sample_id="table-0001", result=_pin(result_path), run_manifest=_pin(run_path)
        ),
        "result_path": result_path,
        "run_path": run_path,
        "request_path": request_path,
        "truth_path": truth_path,
        "base_commit": base_commit,
        "manifest_commit": manifest_commit,
        "run_commit": run_commit,
    }


def _score(root: Path, panel: dict[str, Any]) -> dict[str, Any]:
    return score_tatr_structure_panel(
        root,
        crop_manifest=panel["manifest"],
        model_request=panel["request"],
        source_gold=panel["truth"],
        tatr_runs=[panel["run"]],
    )


def _reseal_tatr_run(panel: dict[str, Any]) -> None:
    result_path = panel["result_path"]
    run_path = panel["run_path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["metrics"]["query_count"] = len(result["query_predictions"])
    run["artifacts"]["structure_result"] = {
        "path": "structure_result.json",
        "size_bytes": result_path.stat().st_size,
        "sha256": sha256_file(result_path),
    }
    _write_json(run_path, run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=_pin(result_path),
        run_manifest=_pin(run_path),
    )


def _refreeze_panel_before_inference(panel: dict[str, Any]) -> None:
    """Commit intentional fixture changes, then bind the synthetic run to them."""

    panel["truth"] = _pin(panel["truth_path"])
    run_commit = _commit_all(panel["root"], "refreeze test panel before inference")
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = run_commit
    _write_json(panel["run_path"], run)
    panel["run_commit"] = run_commit
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=_pin(panel["result_path"]),
        run_manifest=_pin(panel["run_path"]),
    )


def _mutate_truth_and_refreeze(panel: dict[str, Any], mutate: Any) -> None:
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    mutate(truth["samples"][0])
    _write_json(panel["truth_path"], truth)
    _refreeze_panel_before_inference(panel)


def test_scores_all_fixed_thresholds_without_selecting_from_expected_count(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)

    scored = _score(tmp_path, panel)

    assert scored["status"] == "SCORED_NO_THRESHOLD_SELECTED"
    assert scored["threshold_policy"]["object_score_thresholds"] == list(
        FIXED_OBJECT_SCORE_THRESHOLDS
    )
    assert scored["threshold_policy"]["selected_threshold"] is None
    assert set(scored["threshold_grid"]) == {
        "0.050000",
        "0.300000",
        "0.500000",
        "0.700000",
        "0.900000",
    }
    low = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"]
    high = scored["threshold_grid"]["0.900000"]["iou_thresholds"]["0.50"]["samples"]
    assert low["table-0001"]["topology"]["exact_topology"] is True
    assert low["table-0001"]["value_assignment"]["source_anchored_value_assignment_exact"] is True
    assert high["table-0001"]["retained_query_count"] == 0
    assert high["table-0001"]["topology"]["exact_topology"] is False
    assert scored["promotion_decision"]["selected_threshold"] is None


def test_iou_assignment_is_lexicographically_maximum_cardinality_before_iou() -> None:
    size = 8
    ious = [[0.0] * size for _ in range(size)]
    for index in range(size):
        ious[index][index] = 0.5
    for index in range(size - 1):
        ious[index][index + 1] = 0.99

    assignment = _maximum_weight_assignment(_cardinality_primary_weights(ious, 0.5))
    valid = [(row, column) for row, column in assignment if ious[row][column] >= 0.5]

    # A fixed `2 + IoU` weight incorrectly chooses seven 0.99 edges.  The
    # scorer must first retain all eight valid matches, then maximize IoU.
    assert valid == [(index, index) for index in range(size)]


def test_unscorable_class_is_not_converted_to_a_zero_instance_success(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    truth["samples"][0]["class_coverage"]["table spanning cell"] = "UNSCORABLE"
    _write_json(panel["truth_path"], truth)
    _refreeze_panel_before_inference(panel)

    scored = _score(tmp_path, panel)

    metric = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["class_metrics"]["table spanning cell"]
    assert metric == {"coverage": "UNSCORABLE", "metrics": None, "matches": []}


def test_rejects_self_consistent_result_rewrite_without_external_hash_update(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][2]["bbox_source_pixels_xyxy"] = [0.0, 60.0, 100.0, 90.0]
    _write_json(panel["result_path"], result)

    with pytest.raises(TatrStructureCalibrationError, match="result is missing or hash-drifted"):
        _score(tmp_path, panel)


def test_rejects_truth_rewrite_without_external_hash_update(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    truth["samples"][0]["logical_row_count"] = 4
    _write_json(panel["truth_path"], truth)

    with pytest.raises(
        TatrStructureCalibrationError, match="source gold is missing or hash-drifted"
    ):
        _score(tmp_path, panel)


def test_rejects_reauthored_and_externally_repinned_gold_after_tatr_run(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    truth["samples"][0]["logical_row_count"] = 4
    _write_json(panel["truth_path"], truth)
    panel["truth"] = _pin(panel["truth_path"])

    with pytest.raises(TatrStructureCalibrationError, match="frozen blob at declared commit"):
        _score(tmp_path, panel)


def test_rejects_gold_pin_whose_path_was_untracked_at_tatr_run_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    relocated = _write_json(
        tmp_path / "untracked/source-gold.json",
        json.loads(panel["truth_path"].read_text(encoding="utf-8")),
    )
    panel["truth"] = _pin(relocated)

    with pytest.raises(TatrStructureCalibrationError, match="missing or untracked"):
        _score(tmp_path, panel)


def test_rejects_gold_input_untracked_at_declared_pre_inference_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    untracked_gold_input = _write_json(
        tmp_path / "runs/untracked-gold-input.json", {"frozen": True}
    )
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    truth["gold_input_ref"] = _ref(untracked_gold_input, tmp_path)
    _write_json(panel["truth_path"], truth)
    _refreeze_panel_before_inference(panel)

    with pytest.raises(
        TatrStructureCalibrationError, match="source-gold input.*missing or untracked"
    ):
        _score(tmp_path, panel)


def test_rejects_source_spec_reauthored_and_repinned_after_tatr_run(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    manifest = json.loads(panel["manifest"].path.read_text(encoding="utf-8"))
    source_spec = tmp_path / manifest["source_spec_ref"]["path"]
    _write_json(source_spec, {"frozen": True, "post_run_rewrite": True})
    manifest["source_spec_ref"] = _ref(source_spec, tmp_path)
    _write_json(panel["manifest"].path, manifest)
    panel["manifest"] = _pin(panel["manifest"].path)
    request = json.loads(panel["request"].path.read_text(encoding="utf-8"))
    request["crop_manifest"] = {
        "path": panel["manifest"].path.relative_to(tmp_path).as_posix(),
        "sha256": panel["manifest"].sha256,
        "size_bytes": panel["manifest"].path.stat().st_size,
    }
    _write_json(panel["request"].path, request)
    panel["request"] = _pin(panel["request"].path)
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    truth["crop_manifest"] = request["crop_manifest"]
    _write_json(panel["truth_path"], truth)
    panel["truth"] = _pin(panel["truth_path"])

    with pytest.raises(TatrStructureCalibrationError, match="source panel spec did not match"):
        _score(tmp_path, panel)


def test_rejects_reference_or_expected_structure_exposure_in_model_request(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    request = json.loads(panel["request_path"].read_text(encoding="utf-8"))
    request["expected_structure_available_to_reader"] = True
    _write_json(panel["request_path"], request)
    panel["request"] = _pin(panel["request_path"])

    with pytest.raises(TatrStructureCalibrationError, match="reference-blind boundary"):
        _score(tmp_path, panel)


@pytest.mark.parametrize("target", ["sample", "object", "anchor"])
def test_rejects_non_allowlisted_fields_anywhere_in_source_gold(
    tmp_path: Path, target: str
) -> None:
    panel = _build_panel(tmp_path)

    def mutate(sample: dict[str, Any]) -> None:
        if target == "sample":
            sample["leaked_family_hint"] = "secret"
        elif target == "object":
            sample["gold_objects"][0]["bank_hint"] = "secret"
        else:
            sample["value_anchors"][0]["ocr_text"] = "secret"

    _mutate_truth_and_refreeze(panel, mutate)

    with pytest.raises(TatrStructureCalibrationError, match="non-allowlisted fields"):
        _score(tmp_path, panel)


def test_rejects_visible_dash_axis_overlapping_source_anchored_value_cell(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)

    def mutate(sample: dict[str, Any]) -> None:
        sample["numeric_lane_count"] = 2
        sample["visible_unscored_dash_cells"] = [
            {
                "logical_row_ordinal": 1,
                "numeric_lane_ordinal": 1,
                "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
            }
        ]
        summary = sample["value_cell_coverage_summary"]
        summary["source_anchored_value_cell_count"] = 1
        summary["visible_unscored_dash_cell_count"] = 1
        summary["cell_slot_count"] = 2
        summary["other_unanchored_cell_count"] = 0

    _mutate_truth_and_refreeze(panel, mutate)

    with pytest.raises(TatrStructureCalibrationError, match="overlaps"):
        _score(tmp_path, panel)


def test_reports_visible_dash_denominator_without_penalizing_or_inventing_boxes(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)

    def mutate(sample: dict[str, Any]) -> None:
        sample["numeric_lane_count"] = 3
        sample["visible_unscored_dash_cells"] = [
            {
                "logical_row_ordinal": 1,
                "numeric_lane_ordinal": lane,
                "reason": "VISIBLE_DASH_NO_AUTHENTICATED_SOURCE_LINE",
            }
            for lane in (2, 3)
        ]
        sample["value_cell_coverage_summary"] = {
            "cell_slot_count": 3,
            "source_anchored_value_cell_count": 1,
            "visible_unscored_dash_cell_count": 2,
            "other_unanchored_cell_count": 0,
        }

    _mutate_truth_and_refreeze(panel, mutate)

    scored = _score(tmp_path, panel)

    for threshold in scored["threshold_grid"].values():
        for by_iou in threshold["iou_thresholds"].values():
            assignment = by_iou["samples"]["table-0001"]["value_assignment"]
            assert assignment["scope"] == (
                "SOURCE_LINE_ANCHORS_ONLY_NOT_FULL_VISIBLE_CELL_COVERAGE"
            )
            assert assignment["full_visible_cell_coverage_claimed"] is False
            assert assignment["cell_coverage"]["cell_slot_count"] == 3
            assert assignment["cell_coverage"]["source_anchored_value_cell_count"] == 1
            assert assignment["cell_coverage"]["visible_unscored_dash_cell_count"] == 2
            assert (
                assignment["cell_coverage"]["visible_unscored_dash_cells_scored_or_penalized"]
                is False
            )
            assert len(assignment["visible_unscored_dash_cells"]) == 2
    exact_assignment = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["value_assignment"]
    assert exact_assignment["source_anchored_value_assignment_exact"] is True
    partial_topology = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["topology"]
    assert partial_topology["source_anchored_numeric_lane_count"] == 1
    assert partial_topology["expected_numeric_lane_count"] == 3
    assert partial_topology["exact_numeric_lane_assignment"] is False
    assert partial_topology["exact_topology"] is False


def test_rejects_manifest_sample_text_or_family_leak_even_if_firewall_claims_false(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    manifest = json.loads(panel["manifest"].path.read_text(encoding="utf-8"))
    manifest["samples"][0]["family"] = "LEAKED_ACCOUNTING_FAMILY"
    manifest["samples"][0]["ocr_text"] = "LEAKED VIETNAMESE TEXT"
    _write_json(panel["manifest"].path, manifest)
    panel["manifest"] = _pin(panel["manifest"].path)
    request = json.loads(panel["request"].path.read_text(encoding="utf-8"))
    request["crop_manifest"]["sha256"] = panel["manifest"].sha256
    request["crop_manifest"]["size_bytes"] = panel["manifest"].path.stat().st_size
    _write_json(panel["request"].path, request)
    panel["request"] = _pin(panel["request"].path)

    with pytest.raises(TatrStructureCalibrationError, match="sample 0 is not an object"):
        _score(tmp_path, panel)


def test_rejects_manifest_crop_pixels_not_replayed_from_bound_source_render(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    from PIL import Image

    Image.new("RGB", (100, 100), "black").save(
        panel["manifest"].path.parent / "crops/table-0001.png"
    )
    crop = panel["manifest"].path.parent / "crops/table-0001.png"
    manifest = json.loads(panel["manifest"].path.read_text(encoding="utf-8"))
    manifest["samples"][0]["crop_sha256"] = sha256_file(crop)
    _write_json(panel["manifest"].path, manifest)
    panel["manifest"] = _pin(panel["manifest"].path)
    request = json.loads(panel["request"].path.read_text(encoding="utf-8"))
    request["crop_manifest"] = {
        "path": panel["manifest"].path.relative_to(tmp_path).as_posix(),
        "sha256": panel["manifest"].sha256,
        "size_bytes": panel["manifest"].path.stat().st_size,
    }
    request["samples"][0]["crop_sha256"] = sha256_file(crop)
    _write_json(panel["request"].path, request)
    panel["request"] = _pin(panel["request"].path)

    with pytest.raises(TatrStructureCalibrationError, match="crop pixels do not equal"):
        _score(tmp_path, panel)


def test_geometry_only_score_cannot_promote_without_downstream_graph_assessment(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)

    scored = _score(tmp_path, panel)

    downstream = scored["downstream_promotion"]
    assert downstream["status"] == "NOT_PROVIDED"
    assert not any(downstream["downstream_gate_pass_by_threshold"].values())
    assert "Geometry alone" in downstream["reason"]
    assert scored["promotion_decision"]["eligible_thresholds"] == []
    assert scored["promotion_decision"]["decision"] == (
        "NO_PROMOTION_CALIBRATION_ONLY_NO_TRUSTED_BASELINE_HOLDOUT_OR_RUNTIME_BUDGET"
    )
    assert scored["promotion_decision"]["untouched_holdout_evaluation_present"] is False


def test_self_declared_source_geometry_baseline_is_rejected_from_promotion(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    manifest_path = panel["manifest"].path
    request_path = panel["request"].path
    baseline_path = _write_json(
        tmp_path / "baseline.json",
        {
            "format_version": "SOURCE_PPOCRV6_GEOMETRY_BASELINE_V1",
            "state": "REFERENCE_BLIND_SOURCE_GEOMETRY_BASELINE_COMPLETE",
            "crop_manifest": {
                "path": manifest_path.relative_to(tmp_path).as_posix(),
                "sha256": sha256_file(manifest_path),
                "size_bytes": manifest_path.stat().st_size,
            },
            "model_request": {
                "path": request_path.relative_to(tmp_path).as_posix(),
                "sha256": sha256_file(request_path),
            },
            "sample_count": 1,
            "samples": [
                {
                    "sample_id": "table-0001",
                    "runtime": {"wall_seconds": 0.1, "peak_ram_mib": 20.0},
                    "predictions": [
                        {
                            "label": "table",
                            "bbox_crop_pixels_xyxy": [0.0, 0.0, 100.0, 100.0],
                        },
                        {
                            "label": "table column",
                            "bbox_crop_pixels_xyxy": [50.0, 0.0, 100.0, 100.0],
                        },
                        {
                            "label": "table row",
                            "bbox_crop_pixels_xyxy": [0.0, 20.0, 100.0, 50.0],
                        },
                        {
                            "label": "table column header",
                            "bbox_crop_pixels_xyxy": [0.0, 0.0, 100.0, 20.0],
                        },
                    ],
                }
            ],
        },
    )

    scored = score_tatr_structure_panel(
        tmp_path,
        crop_manifest=panel["manifest"],
        model_request=panel["request"],
        source_gold=panel["truth"],
        tatr_runs=[panel["run"]],
        deterministic_baseline=_pin(baseline_path),
    )

    baseline = scored["source_ppocrv6_geometry_baseline"]
    assert baseline["status"] == "REJECTED_UNTRUSTED_SELF_DECLARED_BASELINE_V1"
    assert baseline["comparison"] is None
    assert "No pinned pre-truth" in baseline["reason"]
    assert scored["promotion_decision"]["candidate_thresholds_before_runtime_budget"] == []
    assert scored["promotion_decision"]["eligible_thresholds"] == []


def test_value_assignment_uses_exact_iou_match_not_higher_score_huge_covering_row(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][4] = _query(
        4, "table row", [0.0, 0.0, 100.0, 100.0], object_score=0.85
    )
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    scored = _score(tmp_path, panel)

    sample = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"]["table-0001"]
    anchor = sample["value_assignment"]["anchors"][0]
    assert sample["topology"]["exact_topology"] is False  # the huge row remains an FP
    assert anchor["row"]["query_index"] == 2
    assert anchor["row"]["matched_gold_object_id"] == "row-1"
    assert anchor["row"]["localized_to_expected_gold_object"] is True
    assert anchor["row_correct"] is True


def test_huge_column_matched_at_iou_half_is_rejected_for_value_assignment(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][1] = _query(1, "table column", [0.0, 0.0, 100.0, 100.0])
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    scored = _score(tmp_path, panel)

    sample = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"]["table-0001"]
    column = sample["value_assignment"]["anchors"][0]["column"]
    assert column["matched_gold_object_id"] == "numeric-column"
    assert column["prediction_gold_iou"] == 0.5
    assert column["prediction_to_gold_area_ratio"] == 2.0
    assert column["localized_to_expected_gold_object"] is False
    assert "PREDICTION_GOLD_IOU_TOO_LOW_FOR_VALUE_ASSIGNMENT" in column["failure_reasons"]
    assert "PREDICTION_GOLD_AREA_RATIO_OUTSIDE_STRICT_BOUNDS" in column["failure_reasons"]
    assert sample["value_assignment"]["anchors"][0]["column_correct"] is False
    assert sample["topology"]["exact_numeric_lane_assignment"] is False


def test_shifted_row_matched_at_iou_half_is_rejected_for_value_assignment(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][2] = _query(2, "table row", [0.0, 10.0, 100.0, 40.0])
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    scored = _score(tmp_path, panel)

    sample = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"]["table-0001"]
    row = sample["value_assignment"]["anchors"][0]["row"]
    assert row["matched_gold_object_id"] == "row-1"
    assert row["prediction_gold_iou"] == 0.5
    assert row["anchor_coverage"] == 1.0
    assert row["localized_to_expected_gold_object"] is False
    assert "PREDICTION_GOLD_IOU_TOO_LOW_FOR_VALUE_ASSIGNMENT" in row["failure_reasons"]
    assert "PREDICTION_CENTER_TOO_FAR_FROM_EXPECTED_GOLD_CENTER" in row["failure_reasons"]
    assert sample["value_assignment"]["anchors"][0]["row_correct"] is False


def test_header_row_axis_is_separate_from_column_header_object_axis(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    truth = json.loads(panel["truth_path"].read_text(encoding="utf-8"))
    sample_truth = truth["samples"][0]
    sample_truth["header_row_count"] = 2
    sample_truth["gold_objects"].extend(
        [
            {
                "object_id": "header-row-1",
                "label": "table row",
                "bbox_crop_pixels_xyxy": [0.0, 0.0, 100.0, 10.0],
            },
            {
                "object_id": "header-row-2",
                "label": "table row",
                "bbox_crop_pixels_xyxy": [0.0, 10.0, 100.0, 20.0],
            },
        ]
    )
    _write_json(panel["truth_path"], truth)
    _refreeze_panel_before_inference(panel)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][4] = _query(4, "table row", [0.0, 0.0, 100.0, 10.0])
    result["query_predictions"][5] = _query(5, "table row", [0.0, 10.0, 100.0, 20.0])
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    scored = _score(tmp_path, panel)

    topology = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["topology"]
    assert topology["declared_header_row_count"] == 2
    assert topology["declared_body_logical_row_count"] == 1
    assert topology["predicted_row_count"] == 3
    assert topology["expected_table_row_object_count"] == 3
    assert topology["predicted_column_header_object_count"] == 1
    assert topology["expected_column_header_object_count"] == 1
    assert topology["exact_column_header_object_count"] is True
    assert topology["exact_topology"] is True


def test_equal_structure_counts_do_not_claim_exact_topology_when_header_geometry_misses(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][3] = _query(3, "table column header", [0.0, 80.0, 100.0, 100.0])
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    scored = _score(tmp_path, panel)

    topology = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["topology"]
    assert topology["all_scorable_class_counts_exact"] is True
    assert topology["all_scorable_geometry_exact_at_iou_threshold"] is False
    assert topology["exact_topology"] is False


def test_exact_row_topology_counts_header_and_projected_rows_in_tatr_row_axis(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)

    scored = _score(tmp_path, panel)

    topology = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"][
        "table-0001"
    ]["topology"]
    assert topology["declared_body_logical_row_count"] == 1
    assert topology["expected_table_row_object_count"] == 1
    assert topology["exact_table_row_object_count"] is True


def test_degenerate_raw_query_is_authenticated_but_not_retained(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][4] = {
        **_query(4, "table row", [0.0, 0.0, 0.0, 50.0]),
        "bbox_status": "DEGENERATE",
    }
    _write_json(panel["result_path"], result)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["metrics"]["query_count"] = 125
    run["artifacts"]["structure_result"] = {
        "path": "structure_result.json",
        "size_bytes": panel["result_path"].stat().st_size,
        "sha256": sha256_file(panel["result_path"]),
    }
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=_pin(panel["result_path"]),
        run_manifest=_pin(panel["run_path"]),
    )

    scored = _score(tmp_path, panel)

    sample = scored["threshold_grid"]["0.500000"]["iou_thresholds"]["0.50"]["samples"]["table-0001"]
    assert sample["retained_query_count"] == 4
    assert sample["retained_counts_by_label"]["table row"] == 1


def test_rejects_recomputed_result_and_run_with_inconsistent_normalized_geometry(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"][2]["bbox_source_pixels_xyxy"] = [0.0, 60.0, 100.0, 90.0]
    _write_json(panel["result_path"], result)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["artifacts"]["structure_result"] = {
        "path": "structure_result.json",
        "size_bytes": panel["result_path"].stat().st_size,
        "sha256": sha256_file(panel["result_path"]),
    }
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=_pin(panel["result_path"]),
        run_manifest=_pin(panel["run_path"]),
    )

    with pytest.raises(TatrStructureCalibrationError, match="coordinate systems disagree"):
        _score(tmp_path, panel)


def test_accepts_clean_descendant_run_commit_after_frozen_manifest_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)

    scored = _score(tmp_path, panel)

    assert panel["run_commit"] != panel["manifest_commit"]
    assert scored["status"] == "SCORED_NO_THRESHOLD_SELECTED"


def test_commit_ancestry_helper_allows_exact_freeze_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)

    _verify_clean_descendant_run_commit(
        tmp_path,
        frozen_commit=panel["manifest_commit"],
        run_commit=panel["manifest_commit"],
        sample_id="table-0001",
    )


def test_rejects_clean_run_commit_that_is_ancestor_not_descendant_of_freeze(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = panel["base_commit"]
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )

    with pytest.raises(TatrStructureCalibrationError, match="not a descendant"):
        _score(tmp_path, panel)


def test_rejects_missing_or_malformed_run_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = "c" * 40
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )
    with pytest.raises(TatrStructureCalibrationError, match="commit is absent"):
        _score(tmp_path, panel)

    panel = _build_panel(tmp_path / "malformed")
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = "not-a-commit"
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )
    with pytest.raises(TatrStructureCalibrationError, match="run commit is invalid"):
        _score(tmp_path / "malformed", panel)


def test_rejects_existing_but_unrelated_run_commit(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    empty_tree = _git(tmp_path, "mktree", input_bytes=b"")
    unrelated_commit = _git(tmp_path, "commit-tree", empty_tree, "-m", "unrelated")
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = unrelated_commit
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )

    with pytest.raises(TatrStructureCalibrationError, match="not a descendant"):
        _score(tmp_path, panel)


def test_rejects_rehashed_run_when_pinned_safety_or_processor_drifts(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["safety"]["value_authority"] = True
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )
    with pytest.raises(TatrStructureCalibrationError, match="safety authority drifted"):
        _score(tmp_path, panel)

    panel = _build_panel(tmp_path / "processor")
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["configuration"]["runtime_processor_size"]["longest_edge"] = 1024
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )
    with pytest.raises(TatrStructureCalibrationError, match="processor, or runner identity"):
        _score(tmp_path / "processor", panel)

    panel = _build_panel(tmp_path / "parameter-count")
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["runtime"]["model"]["loaded_parameter_count"] = 28_847_819
    run["runtime"]["model"]["loaded_state_element_count"] = 28_828_619
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )
    with pytest.raises(TatrStructureCalibrationError, match="checkpoint identity"):
        _score(tmp_path / "parameter-count", panel)


def test_rejects_clean_descendant_run_commit_with_modified_runner_then_restored_worktree(
    tmp_path: Path,
) -> None:
    panel = _build_panel(tmp_path)
    runner = tmp_path / "scripts/models/run_tatr_structure.py"
    original = runner.read_bytes()
    runner.write_bytes(original + b"\n# adversarial clean runner commit\n")
    modified_runner_commit = _commit_all(tmp_path, "modify runner before inference")
    runner.write_bytes(original)
    run = json.loads(panel["run_path"].read_text(encoding="utf-8"))
    run["code"]["commit"] = modified_runner_commit
    _write_json(panel["run_path"], run)
    panel["run"] = TatrRunPin(
        sample_id="table-0001",
        result=panel["run"].result,
        run_manifest=_pin(panel["run_path"]),
    )

    with pytest.raises(TatrStructureCalibrationError, match="TATR runner did not match"):
        _score(tmp_path, panel)


def test_rejects_rehashed_run_with_wrong_query_denominator(tmp_path: Path) -> None:
    panel = _build_panel(tmp_path)
    result = json.loads(panel["result_path"].read_text(encoding="utf-8"))
    result["query_predictions"].pop()
    _write_json(panel["result_path"], result)
    _reseal_tatr_run(panel)

    with pytest.raises(TatrStructureCalibrationError, match="query denominator drifted"):
        _score(tmp_path, panel)
