from __future__ import annotations

import copy
import inspect
import json
import os
import tomllib
from pathlib import Path

import pytest
from PIL import Image

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation import qwen35_logical_row_output_seal as output_seal
from bctc_ai.evaluation.qwen35_logical_row_output_seal import (
    Qwen35LogicalRowOutputSealError,
    seal_qwen35_logical_row_output,
)

HEAD = "a" * 40
CONFIG_PATH = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml")
AUTHORIZATION_PATH = Path(
    "docs/experiments/E-0036-qwen-reference-blind-inference-authorization.json"
)
REQUEST_PATH = Path("output/calibration/e0036-mbb-cdkt-semantic-label-readers/request.json")
OUTPUT_DIRECTORY = Path("output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader")
SEAL_PATH = Path("docs/experiments/E-0036-qwen-output-seal.json")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _fake_git(_project_root: Path, *arguments: str) -> str:
    if arguments == ("status", "--porcelain"):
        return ""
    if arguments == ("rev-parse", "HEAD"):
        return HEAD
    raise AssertionError(arguments)


def _build_complete_output(tmp_path: Path, project_root: Path) -> dict[str, object]:
    root = tmp_path / "project"
    config = copy.deepcopy(tomllib.loads((project_root / CONFIG_PATH).read_text(encoding="utf-8")))
    model_config_path = root / CONFIG_PATH
    model_config_path.parent.mkdir(parents=True, exist_ok=True)
    model_config_path.write_text("predeclared Qwen config\n", encoding="utf-8")
    authorization = {
        "decision": "RUN_QWEN_SAME_REQUEST",
    }
    authorization_path = root / AUTHORIZATION_PATH
    _write_json(authorization_path, authorization)
    config["authorization"]["path"] = AUTHORIZATION_PATH.as_posix()
    config["authorization"]["sha256"] = sha256_file(authorization_path)
    config["authorization"]["size_bytes"] = authorization_path.stat().st_size

    crop_manifest_path = Path("output/calibration/e0035/crop_manifest.json")
    _write_json(root / crop_manifest_path, {"state": "FROZEN"})
    request_samples: list[dict[str, str]] = []
    for index in range(64):
        crop_path = Path(f"output/calibration/e0035/crops/crop-{index:03d}.png")
        crop = root / crop_path
        crop.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (200, 70), color=(index, index, index)).save(crop, format="PNG")
        request_samples.append(
            {
                "sample_id": f"page-0003-row-{index:03d}-label",
                "category": "LOGICAL_ROW_LABEL",
                "crop_path": crop_path.as_posix(),
                "crop_sha256": sha256_file(crop),
            }
        )
    request = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "state": "READY_FOR_REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE",
        "dataset_role": "CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_LOGICAL_ROW_LABEL_PROPOSAL_ONLY",
        "git_commit": HEAD,
        "git_dirty": False,
        "crop_manifest": {
            "path": crop_manifest_path.as_posix(),
            "sha256": sha256_file(root / crop_manifest_path),
        },
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": request_samples,
    }
    request_path = root / REQUEST_PATH
    _write_json(request_path, request)
    config["request"]["path"] = REQUEST_PATH.as_posix()
    config["request"]["sha256"] = sha256_file(request_path)
    config["output"]["directory"] = OUTPUT_DIRECTORY.as_posix()
    config["output"]["seal_path"] = SEAL_PATH.as_posix()
    for control_key in ("sealer", "capture_script"):
        control_path = root / config["output"][control_key]["path"]
        control_path.parent.mkdir(parents=True, exist_ok=True)
        control_path.write_text(f"predeclared {control_key}\n", encoding="utf-8")

    result_samples = [
        {
            **sample,
            "crop_width": 200,
            "crop_height": 70,
            "input_token_count": 96,
            "visual_token_count": 66,
            "generated_token_ids": [100, 248046],
            "forbidden_generated_control_token_ids": [],
            "raw_generated_output": "Tài sản<|im_end|>",
            "raw_output": "Tài sản",
            "nonempty_line_count": 1,
            "generated_token_count": 2,
            "terminated_by_eos": True,
            "status": "PARSED_SEMANTIC_PROPOSAL_ONLY",
            "proposal_text": "Tài sản",
            "reader_score": None,
            "reader_score_available": False,
            "inference_seconds": 1.0,
        }
        for sample in request_samples
    ]
    result = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "QWEN3_5_27B_GPTQ_INT4",
        "state": "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE",
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "reference_text_available_to_reader": False,
        "sample_count": 64,
        "samples": result_samples,
        "authority": {key: False for key in config["safety"]},
    }
    output_directory = root / OUTPUT_DIRECTORY
    result_path = output_directory / "ocr_result.json"
    _write_json(result_path, result)
    result_record = {
        "path": "ocr_result.json",
        "size_bytes": result_path.stat().st_size,
        "sha256": sha256_file(result_path),
    }

    inference = config["inference"]
    device_map = config["device_map"]
    overlay = config["runtime_overlay"]
    compatibility = config["runtime_compatibility"]
    model_artifacts = output_seal._expected_model_artifacts(config)
    minimum_free_vram = (
        device_map["estimated_registered_tensor_bytes_gpu"]
        + device_map["minimum_runtime_vram_headroom_bytes"]
    )
    manifest = {
        "format_version": 1,
        "experiment_id": "E-0036",
        "reader": "QWEN3_5_27B_GPTQ_INT4",
        "state": "REFERENCE_BLIND_LOGICAL_ROW_LABEL_INFERENCE_COMPLETE",
        "dataset_role": "CALIBRATION",
        "evidence_role": config["evidence_role"],
        "git_commit": HEAD,
        "git_dirty": False,
        "authorization": {
            "path": AUTHORIZATION_PATH.as_posix(),
            "sha256": sha256_file(authorization_path),
            "decision": authorization["decision"],
            "reference_content_available_to_reader": False,
        },
        "request": {
            "path": REQUEST_PATH.as_posix(),
            "sha256": sha256_file(request_path),
        },
        "crop_manifest": request["crop_manifest"],
        "configuration": {
            "path": CONFIG_PATH.as_posix(),
            "sha256": sha256_file(model_config_path),
            "prompt": inference["prompt"],
            "aspect_preservation": inference["aspect_preservation"],
            "processor_min_pixels": inference["processor_min_pixels"],
            "processor_max_pixels": inference["processor_max_pixels"],
            "processor_use_fast": False,
            "context_length": inference["context_length"],
            "maximum_new_tokens": inference["maximum_new_tokens"],
            "enable_thinking": False,
            "do_sample": False,
            "network_policy": "PYTHON_AUDIT_ALL_SOCKET_EVENTS_DENIED",
            "deterministic_algorithms": True,
            "linear_attention_implementation": "TRANSFORMERS_TORCH_FALLBACK",
            "execution_model": "ONE_SHOT_PROCESS_REQUIRED",
            "network_audit_hook_persists_until_process_exit": True,
            "hard_watchdog_seconds_per_sample": inference["maximum_sample_inference_seconds"],
        },
        "runtime": {
            "packages": compatibility["packages"],
            "overlay_tree_identity": {
                "file_count": overlay["installed_tree_file_count"],
                "total_bytes": overlay["installed_tree_total_bytes"],
                "pyc_file_count": overlay["installed_tree_pyc_file_count"],
                "tree_sha256": overlay["installed_tree_sha256"],
            },
            "torch_cuda": compatibility["cuda_runtime"],
            "gpu_name": "NVIDIA GeForce RTX 4090",
            "compute_capability": compatibility["minimum_compute_capability"],
            "bf16_supported": True,
            "host_available_memory_bytes_before_load": compatibility[
                "minimum_host_available_memory_bytes"
            ],
            "host_available_memory_bytes_after_inference": 40_000_000_000,
            "hf_device_map": {key: str(value) for key, value in device_map["modules"].items()},
            "weight_map_coverage": {
                "weight_index_tensor_count": device_map["expected_weight_index_tensor_count"],
                "device_map_covered_tensor_count": device_map[
                    "expected_device_map_covered_tensor_count"
                ],
                "excluded_auxiliary_mtp_tensor_count": device_map[
                    "expected_excluded_auxiliary_mtp_tensor_count"
                ],
            },
            "gptq_backend": "gptq_triton",
            "gptq_dynamic_exclusion_keys": sorted(config["quantization"]["dynamic_exclusion_keys"]),
            "quantized_linear_module_count": config["quantization"][
                "expected_quantized_linear_module_count"
            ],
            "quantized_placeholder_initialization": {
                "mechanism": "GPTQ_META_AFTER_CPU_SOURCE_SHAPE_VALIDATION",
                "module_count": config["quantization"]["expected_quantized_linear_module_count"],
                "buffer_count": compatibility["native_shell_quantized_placeholder_buffer_count"],
                "buffer_names": compatibility["native_shell_quantized_placeholder_buffer_names"],
                "nominal_buffer_bytes": compatibility["native_shell_quantized_buffer_bytes"],
                "placeholder_device": compatibility["native_shell_quantized_placeholder_device"],
                "hooks_restored_after_load": True,
                "materialized_after_checkpoint_load": True,
            },
            "temporary_load_staging": {
                "persistent_weight_device_map_disk": False,
                "controlled_root": "/tmp/qwen-model-cache",
                "ephemeral_directory_name": "qwen-e0036-load-test",
                "triton_cache_is_ephemeral": True,
                "torchinductor_cache_is_ephemeral": True,
                "free_bytes_before_load": device_map["temporary_load_staging_minimum_free_bytes"],
                "minimum_free_bytes_required": device_map[
                    "temporary_load_staging_minimum_free_bytes"
                ],
            },
            "hard_watchdog": {
                "path": config["hard_watchdog"]["path"],
                "sha256": config["hard_watchdog"]["sha256"],
                "timeout_seconds_per_sample": inference["maximum_sample_inference_seconds"],
                "mechanism": "LINUX_PIDFD_EXTERNAL_SIGKILL",
            },
            "vram_preflight": {
                "free_bytes_before_load": minimum_free_vram,
                "minimum_free_bytes_required": minimum_free_vram,
                "registered_gpu_tensor_bytes": device_map["estimated_registered_tensor_bytes_gpu"],
                "minimum_runtime_headroom_bytes": device_map["minimum_runtime_vram_headroom_bytes"],
            },
            "model": {
                "repo_id": config["model"]["repo_id"],
                "revision": config["model"]["revision"],
                "quantization": config["quantization"],
                "artifacts": model_artifacts,
            },
        },
        "metrics": {
            "model_load_seconds": 10.0,
            "total_wall_seconds": 80.0,
            "mechanism_probe": {
                "sample_id": request_samples[0]["sample_id"],
                "inference_seconds": 1.0,
                "generated_token_count": 2,
                "projected_maximum_total_wall_seconds": 3_082.0,
                "projection_policy": "FIRST_CROP_SECONDS_PER_TOKEN_TIMES_96_TOKENS_TIMES_64",
            },
            "sample_count": 64,
            "parsed_proposal_count": 64,
            "structural_rejection_count": 0,
            "minimum_visual_tokens": 66,
            "maximum_visual_tokens": 66,
            "peak_gpu_memory_allocated_mib": 20_000.0,
            "peak_gpu_memory_reserved_mib": 21_000.0,
            "free_vram_bytes_after_inference": 1_000_000_000,
            "total_vram_bytes": 25_000_000_000,
        },
        "started_at": "2026-08-07T08:00:00+00:00",
        "completed_at": "2026-08-07T08:02:00+00:00",
        "safety": {key: False for key in config["safety"]},
        "artifacts": {"ocr_result": result_record},
    }
    manifest_path = output_directory / "run_manifest.json"
    _write_json(manifest_path, manifest)
    return {
        "root": root,
        "config": config,
        "authorization": authorization,
        "model_config_path": model_config_path,
        "authorization_path": authorization_path,
        "result_path": result_path,
        "manifest_path": manifest_path,
    }


def _patch_controls(monkeypatch, fixture: dict[str, object]) -> None:
    monkeypatch.setattr(output_seal, "_git", _fake_git)
    monkeypatch.setattr(
        output_seal,
        "load_qwen35_logical_row_config",
        lambda *_args: (
            fixture["config"],
            fixture["authorization"],
            fixture["model_config_path"],
            fixture["authorization_path"],
        ),
    )


def test_qwen_output_sealer_validates_and_hash_seals_exact_two_file_output(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)

    seal = seal_qwen35_logical_row_output(
        fixture["root"],
        config_path=CONFIG_PATH,
        output_directory=OUTPUT_DIRECTORY,
        output_path=SEAL_PATH,
    )

    assert seal["state"] == "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS"
    assert seal["reader"]["sample_count"] == 64
    assert seal["reader"]["status_counts"] == {"PARSED_SEMANTIC_PROPOSAL_ONLY": 64}
    assert seal["exact_output_file_count"] == 2
    assert seal["reference_or_human_review_loaded_by_sealer"] is False
    assert (fixture["root"] / SEAL_PATH).is_file()


def test_qwen_output_sealer_rejects_noncanonical_output_path(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="canonical lexical path"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=Path("output/calibration/e0036/alternate-qwen-reader"),
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_sample_or_result_hash_drift(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    result_path = fixture["result_path"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["samples"][0]["proposal_text"] = "tampered"
    _write_json(result_path, result)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="parsed sample evidence drifted"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_manifest_result_binding_drift(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    manifest_path = fixture["manifest_path"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"]["ocr_result"]["sha256"] = "0" * 64
    _write_json(manifest_path, manifest)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="manifest identity drifted"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_recomputes_mechanism_projection(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    manifest = json.loads(fixture["manifest_path"].read_text(encoding="utf-8"))
    manifest["metrics"]["mechanism_probe"]["projected_maximum_total_wall_seconds"] = 3_081.0
    _write_json(fixture["manifest_path"], manifest)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="metrics drifted"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_source_has_no_review_template_or_numeric_dependencies():
    source = inspect.getsource(output_seal)
    for forbidden in (
        "bctc_ai.reference",
        "logical_row_label_review_evaluation",
        "reviewed-mapping-corrections",
        "Bank_CDKT_ReportNormId.xlsx",
        "E-0034-mbb-cdkt-numeric-verification",
    ):
        assert forbidden not in source


def test_qwen_output_sealer_rejects_noncanonical_config_argument(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="canonical lexical path"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=Path("config/models/qwen-alternate.toml"),
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_output_directory_symlink_component(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    output_directory = fixture["root"] / OUTPUT_DIRECTORY
    actual_directory = output_directory.with_name("qwen-reader-real")
    output_directory.rename(actual_directory)
    output_directory.symlink_to(actual_directory, target_is_directory=True)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="symlink component"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_symlinked_request(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    request_path = fixture["root"] / REQUEST_PATH
    real_request = request_path.with_name("request-real.json")
    request_path.rename(real_request)
    request_path.symlink_to(real_request)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="symlink component"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_symlinked_crop_parent(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    crop_parent = fixture["root"] / "output/calibration/e0035/crops"
    real_crop_parent = crop_parent.with_name("crops-real")
    crop_parent.rename(real_crop_parent)
    crop_parent.symlink_to(real_crop_parent, target_is_directory=True)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="symlink component"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_result_mutation_after_validation(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    original_validate = output_seal._validate_result

    def validate_then_mutate(*args, **kwargs):
        samples = original_validate(*args, **kwargs)
        with fixture["result_path"].open("ab") as stream:
            stream.write(b" ")
        return samples

    monkeypatch.setattr(output_seal, "_validate_result", validate_then_mutate)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="changed after validation"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_rejects_late_extra_output_file(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    original_recheck = output_seal._assert_stable_file_unchanged
    calls = 0

    def recheck_then_add_extra(*args, **kwargs):
        nonlocal calls
        original_recheck(*args, **kwargs)
        calls += 1
        if calls == 2:
            (fixture["root"] / OUTPUT_DIRECTORY / "late-extra.json").write_text(
                "{}\n", encoding="utf-8"
            )

    monkeypatch.setattr(output_seal, "_assert_stable_file_unchanged", recheck_then_add_extra)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="exact two-file set"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )


def test_qwen_output_sealer_never_overwrites_racing_destination(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    original_inventory = output_seal._output_inventory_identity
    calls = 0
    raced_payload = b"racing writer\n"

    def inventory_then_race(*args, **kwargs):
        nonlocal calls
        identity = original_inventory(*args, **kwargs)
        calls += 1
        if calls == 2:
            destination = fixture["root"] / SEAL_PATH
            destination.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raced_payload)
        return identity

    monkeypatch.setattr(output_seal, "_output_inventory_identity", inventory_then_race)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match="refusing to overwrite"):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )
    assert (fixture["root"] / SEAL_PATH).read_bytes() == raced_payload


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("crop_width", 201, "sample value drifted"),
        ("input_token_count", 4_001, "sample value drifted"),
        ("raw_generated_output", "Tài sản", "raw/token decoding evidence drifted"),
    ],
)
def test_qwen_output_sealer_rejects_unbound_sample_mechanics(
    tmp_path: Path,
    project_root: Path,
    monkeypatch,
    field: str,
    value: object,
    message: str,
):
    fixture = _build_complete_output(tmp_path, project_root)
    _patch_controls(monkeypatch, fixture)
    result = json.loads(fixture["result_path"].read_text(encoding="utf-8"))
    result["samples"][0][field] = value
    _write_json(fixture["result_path"], result)

    with pytest.raises(Qwen35LogicalRowOutputSealError, match=message):
        seal_qwen35_logical_row_output(
            fixture["root"],
            config_path=CONFIG_PATH,
            output_directory=OUTPUT_DIRECTORY,
            output_path=SEAL_PATH,
        )
