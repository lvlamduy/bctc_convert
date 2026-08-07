from __future__ import annotations

import json

import pytest
import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation import logical_row_label_baseline_seal
from bctc_ai.evaluation.logical_row_label_baseline_seal import (
    LogicalRowLabelBaselineSealError,
    seal_logical_row_label_baselines,
)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _request():
    return {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        "git_commit": "a" * 40,
        "git_dirty": False,
        "crop_manifest": {
            "path": "output/calibration/e0035/crop_manifest.json",
            "sha256": "b" * 64,
        },
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": [
            {
                "sample_id": f"page-0003-row-{index:03d}-label",
                "category": "LOGICAL_ROW_LABEL",
                "crop_path": f"output/calibration/e0035/crops/row-{index:03d}.png",
                "crop_sha256": f"{index:064x}",
            }
            for index in range(64)
        ],
    }


def _result(reader_key, request):
    if reader_key == "vietocr":
        reader = "VIETOCR_VGG_TRANSFORMER"
        evidence_role = request["evidence_role"]
        samples = [
            sample
            | {
                "processed_width": 128,
                "processed_height": 32,
                "raw_prediction": "Nhãn đề xuất",
                "mean_decoded_character_probability": 0.9,
                "wall_seconds": 0.01,
            }
            for sample in request["samples"]
        ]
    else:
        reader = "DEEPSEEK_OCR_2"
        evidence_role = "VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY"
        samples = []
        for index, sample in enumerate(request["samples"]):
            accepted = index < 51
            samples.append(
                sample
                | {
                    "crop_width": 256,
                    "crop_height": 64,
                    "raw_output": "Nhãn đề xuất" if accepted else "",
                    "status": (
                        "PARSED_SEMANTIC_PROPOSAL_ONLY" if accepted else "REJECT_EMPTY_OUTPUT"
                    ),
                    "proposal_text": "Nhãn đề xuất" if accepted else "",
                    "nonempty_line_count": 1 if accepted else 0,
                    "reader_score": None,
                    "reader_score_available": False,
                    "inference_seconds": 0.1,
                }
            )
    return {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": reader,
        "state": "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE",
        "dataset_role": "CALIBRATION",
        "evidence_role": evidence_role,
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": samples,
        "authority": {"mapping_authority": False},
    }


def _build_fixture(project_root):
    request = _request()
    request_path = project_root / "output/e0036/request.json"
    _write_json(request_path, request)
    baseline_records = {}
    for reader_key in ("vietocr", "deepseek_ocr2"):
        model_config = project_root / f"config/{reader_key}.toml"
        model_config.parent.mkdir(parents=True, exist_ok=True)
        model_config.write_text("version = 1\n", encoding="utf-8")
        output_directory = project_root / f"output/e0036/{reader_key}"
        result_path = output_directory / "ocr_result.json"
        _write_json(result_path, _result(reader_key, request))
        reader = "VIETOCR_VGG_TRANSFORMER" if reader_key == "vietocr" else "DEEPSEEK_OCR_2"
        metrics = {"sample_count": 64}
        if reader_key == "deepseek_ocr2":
            metrics |= {"parsed_proposal_count": 51, "structural_rejection_count": 13}
        manifest = {
            "format_version": 1,
            "experiment_id": "E-0036",
            "reader": reader,
            "state": "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE",
            "git_commit": request["git_commit"],
            "git_dirty": False,
            "request": {
                "path": "output/e0036/request.json",
                "sha256": sha256_file(request_path),
            },
            "crop_manifest": request["crop_manifest"],
            "configuration": {
                "path": f"config/{reader_key}.toml",
                "sha256": sha256_file(model_config),
            },
            "metrics": metrics,
            "safety": {"mapping_authority": False},
            "artifacts": {
                "ocr_result": {
                    "path": "ocr_result.json",
                    "size_bytes": result_path.stat().st_size,
                    "sha256": sha256_file(result_path),
                }
            },
        }
        _write_json(output_directory / "run_manifest.json", manifest)
        baseline_records[reader_key] = {
            "output_directory": f"output/e0036/{reader_key}",
            "model_config": {
                "path": f"config/{reader_key}.toml",
                "sha256": sha256_file(model_config),
            },
        }
    config = {
        "version": 1,
        "experiment_id": "E-0036",
        "dataset_role": "CALIBRATION",
        "request": {"output_path": "output/e0036/request.json"},
        "baseline_readers": baseline_records,
        "authority": {"reviewed_rows_may_be_loaded_before_baseline_seals": False},
    }
    config_path = project_root / "config/e0036.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path, request_path


def _mock_clean_git(monkeypatch):
    monkeypatch.setattr(
        logical_row_label_baseline_seal,
        "_git",
        lambda _root, *arguments: "" if arguments[0] == "status" else "c" * 40,
    )
    monkeypatch.setattr(
        logical_row_label_baseline_seal,
        "_git_is_ancestor",
        lambda *_arguments: True,
    )


def test_seal_binds_both_outputs_before_review_access(tmp_path, monkeypatch):
    project_root = tmp_path.resolve()
    config_path, request_path = _build_fixture(project_root)
    _mock_clean_git(monkeypatch)

    seal = seal_logical_row_label_baselines(
        project_root,
        experiment_config_path=config_path.relative_to(project_root),
        request_path=request_path.relative_to(project_root),
        output_path="docs/e0036-seal.json",
    )

    assert seal["state"] == "BASELINE_OUTPUTS_HASH_SEALED_BEFORE_REVIEW_ACCESS"
    assert seal["reference_or_human_review_loaded_by_sealer"] is False
    assert seal["readers"]["vietocr"]["sample_count"] == 64
    assert seal["readers"]["deepseek_ocr2"]["parsed_proposal_count"] == 51
    assert seal["readers"]["deepseek_ocr2"]["structural_rejection_count"] == 13


def test_seal_rejects_result_changed_after_manifest(tmp_path, monkeypatch):
    project_root = tmp_path.resolve()
    config_path, request_path = _build_fixture(project_root)
    result_path = project_root / "output/e0036/vietocr/ocr_result.json"
    result_path.write_text(result_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    _mock_clean_git(monkeypatch)

    with pytest.raises(LogicalRowLabelBaselineSealError, match="manifest drifted"):
        seal_logical_row_label_baselines(
            project_root,
            experiment_config_path=config_path.relative_to(project_root),
            request_path=request_path.relative_to(project_root),
            output_path="docs/e0036-seal.json",
        )
