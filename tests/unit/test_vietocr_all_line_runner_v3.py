from __future__ import annotations

import copy
import hashlib
import inspect
import io
import json
from pathlib import Path

import pytest
from PIL import Image

import bctc_ai.ocr.vietocr_all_line_runner_v3 as runner


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (3, 2), "white").save(output, format="PNG")
    return output.getvalue()


def _fake_freeze(monkeypatch: pytest.MonkeyPatch):
    payload = _png_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    samples = []
    for page_index, line_count in enumerate(runner.EXPECTED_LINE_COUNT_VECTOR, start=1):
        page_id = f"page-{page_index:04d}"
        for line_index in range(line_count):
            samples.append(
                {
                    "crop_png_bytes": payload,
                    "crop_sha256": digest,
                    "page_id": page_id,
                    "sample_id": f"{page_id}-line-{line_index:04d}",
                }
            )
    calls = {"snapshot": 0}

    def snapshot(_capability):
        calls["snapshot"] += 1
        return (
            {
                "freeze_id": "voalrv3:freeze:" + "a" * 64,
                "line_count_vector": list(runner.EXPECTED_LINE_COUNT_VECTOR),
                "page_count": 8,
                "sample_count": runner.EXPECTED_SAMPLE_COUNT,
                "state": "FROZEN_READY_NO_MODEL_RUN",
            },
            tuple(samples),
        )

    monkeypatch.setattr(runner, "read_authenticated_vietocr_all_line_snapshot_v3", snapshot)
    capability = object.__new__(runner.AuthenticatedVietOCRAllLineFreezeV3)
    return capability, calls


def _execution_counts() -> dict[str, int]:
    return {
        "authenticated_batch_accessor_call_count": 1,
        "checkpoint_deserialization_count": 1,
        "formal_run_count": 1,
        "model_build_count": 1,
        "process_input_count": runner.EXPECTED_SAMPLE_COUNT,
        "reader_request_count": 1,
        "result_count": runner.EXPECTED_SAMPLE_COUNT,
        "state_dict_load_count": 1,
        "translate_call_count": runner.EXPECTED_SAMPLE_COUNT,
    }


def _fake_results() -> list[dict[str, object]]:
    payload_digest = hashlib.sha256(_png_bytes()).hexdigest()
    results = []
    ordinal = 0
    for page_index, line_count in enumerate(runner.EXPECTED_LINE_COUNT_VECTOR, start=1):
        page_id = f"page-{page_index:04d}"
        for line_index in range(line_count):
            results.append(
                {
                    "crop_sha256": payload_digest,
                    "mean_decoded_character_probability": 0.75,
                    "page_id": page_id,
                    "processed_height": 32,
                    "processed_width": 96,
                    "raw_prediction": f"proposal {ordinal}",
                    "sample_id": f"{page_id}-line-{line_index:04d}",
                }
            )
            ordinal += 1
    return results


def _prepare_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_root: Path,
) -> tuple[object, dict[str, object]]:
    (tmp_path / "output/development").mkdir(parents=True)
    config_payload = (project_root / runner.CONFIG_PATH).read_bytes()
    binding = {
        "commit": "1" * 40,
        "dirty": False,
        "implementation_refs": [],
        "source_tree_oid": "2" * 40,
    }
    projection = {
        "freeze_id": "voalrv3:freeze:" + "a" * 64,
        "line_count_vector": list(runner.EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "sample_count": runner.EXPECTED_SAMPLE_COUNT,
        "state": "FROZEN_READY_NO_MODEL_RUN",
    }
    runtime_artifacts = {
        name: {"path": name, "sha256": digest, "size_bytes": size}
        for name, (digest, size) in runner._EXPECTED_ARTIFACTS.items()
    }
    monkeypatch.setattr(
        runner,
        "_git",
        lambda _root, *args: (
            f"{tmp_path.resolve()}\n".encode()
            if args == ("rev-parse", "--show-toplevel")
            else pytest.fail(f"unexpected Git call: {args!r}")
        ),
    )
    monkeypatch.setattr(runner, "_git_binding", lambda _root: copy.deepcopy(binding))
    monkeypatch.setattr(
        runner,
        "assert_authenticated_vietocr_all_line_freeze_project_root_v3",
        lambda *_args: None,
    )
    monkeypatch.setattr(runner, "_stable_bytes", lambda _path, _label: config_payload)
    monkeypatch.setattr(
        runner,
        "_collect_freeze",
        lambda _capability: (
            copy.deepcopy(projection),
            tuple(
                {
                    "crop_png_bytes": _png_bytes(),
                    "crop_sha256": result["crop_sha256"],
                    "page_id": result["page_id"],
                    "sample_id": result["sample_id"],
                }
                for result in _fake_results()
            ),
        ),
    )
    monkeypatch.setattr(
        runner,
        "_snapshot_runtime",
        lambda _config: (
            {
                "base_config": b"base",
                "model_config": b"model",
                "weights": b"weights",
                "wheel": b"wheel",
            },
            copy.deepcopy(runtime_artifacts),
        ),
    )
    monkeypatch.setattr(runner, "_verify_wheel_overlay", lambda *_args: None)

    execution = {"calls": 0}

    def execute(_root, _config, _snapshots, _batch):
        execution["calls"] += 1
        return (
            _fake_results(),
            {
                "compute_capability": "8.9",
                "cuda_runtime": "13.0",
                "device_name": "NVIDIA GeForce RTX 4090",
                "packages": copy.deepcopy(runner._EXPECTED_PACKAGES),
                "python_major_minor": "3.11",
                "runtime_root": runner.RUNTIME_ROOT.as_posix(),
            },
            _execution_counts(),
            {
                "model_load_seconds": 1.0,
                "peak_gpu_memory_allocated_mib": 2.0,
                "peak_gpu_memory_reserved_mib": 3.0,
                "total_wall_seconds": 4.0,
            },
        )

    monkeypatch.setattr(runner, "_execute_model", execute)
    return object(), execution


def test_fixed_public_contract_and_exact_freeze_batch_access_once(monkeypatch):
    assert runner.CONFIG_PATH == Path(
        "config/models/vietocr-0.3.13-vgg-transformer-all-line-v3.toml"
    )
    assert runner.RUNTIME_ROOT == Path("/workspace/bctc-ai-runtime/vietocr-0.3.13")
    assert runner.RUN_ROOT == Path(
        "output/development/vietocr-all-line-vgg-transformer-v3/fresh-run"
    )
    assert list(inspect.signature(runner.run_authenticated_vietocr_all_line_v3).parameters) == [
        "project_root",
        "freeze_capability",
    ]

    capability, calls = _fake_freeze(monkeypatch)
    projection, batch = runner._collect_freeze(capability)

    assert projection["sample_count"] == 835
    assert len(batch) == 835
    assert calls == {"snapshot": 1}
    assert [
        sum(sample["page_id"] == f"page-{index:04d}" for sample in batch) for index in range(1, 9)
    ] == list(runner.EXPECTED_LINE_COUNT_VECTOR)


def test_collect_freeze_rejects_non_exact_capability_before_any_accessor(monkeypatch):
    monkeypatch.setattr(
        runner,
        "read_authenticated_vietocr_all_line_snapshot_v3",
        lambda _value: pytest.fail("snapshot accessor must not be called"),
    )

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="exact live"):
        runner._collect_freeze(object())


def test_config_requires_real_toml_booleans(project_root):
    payload = (project_root / runner.CONFIG_PATH).read_bytes()
    assert runner._validate_config(payload)["version"] == 3

    for source in (
        b"network_permitted = false",
        b"onnx = false",
        b"numeric_authority = false",
    ):
        drifted = payload.replace(source, source.replace(b"false", b"0"), 1)
        with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="policy drifted"):
            runner._validate_config(drifted)


def test_success_writes_closed_result_and_run_schemas_once(monkeypatch, tmp_path, project_root):
    capability, execution = _prepare_run(monkeypatch, tmp_path, project_root)

    manifest = runner.run_authenticated_vietocr_all_line_v3(tmp_path, capability)
    output = tmp_path / runner.RUN_ROOT
    attempt = json.loads((output / "attempt.json").read_text())
    result = json.loads((output / "ocr_result.json").read_text())
    stored_run = json.loads((output / "run_manifest.json").read_text())

    assert execution["calls"] == 1
    assert manifest == stored_run
    assert set(attempt) == {
        "attempt_id",
        "claim_boundary",
        "format_version",
        "preflight",
        "started_at",
        "state",
    }
    assert attempt["state"] == "FORMAL_ATTEMPT_STARTED_NO_RESUME_OR_RETRY"
    assert set(result) == {
        "attempt_id",
        "dataset_role",
        "evidence_role",
        "experiment_id",
        "format_version",
        "freeze_id",
        "line_count_vector",
        "page_count",
        "reference_text_available_to_reader",
        "result_id",
        "sample_count",
        "samples",
        "state",
    }
    assert result["format_version"] == runner.RESULT_FORMAT_VERSION
    assert result["state"] == "REFERENCE_BLIND_LINE_INFERENCE_COMPLETE"
    assert result["sample_count"] == len(result["samples"]) == 835
    assert set(result["samples"][0]) == {
        "crop_sha256",
        "mean_decoded_character_probability",
        "page_id",
        "processed_height",
        "processed_width",
        "raw_prediction",
        "sample_id",
    }
    assert set(stored_run) == {
        "artifacts",
        "attempt_id",
        "completed_at",
        "configuration",
        "execution_counts",
        "execution_policy",
        "experiment_id",
        "format_version",
        "git_binding",
        "input",
        "metrics",
        "result_id",
        "run_id",
        "runtime",
        "safety",
        "started_at",
        "state",
    }
    assert stored_run["format_version"] == runner.RUN_FORMAT_VERSION
    assert stored_run["state"] == "FRESH_SINGLE_RUN_COMPLETE"
    assert stored_run["execution_counts"] == _execution_counts()
    assert stored_run["input"] == {
        "freeze_id": "voalrv3:freeze:" + "a" * 64,
        "line_count_vector": list(runner.EXPECTED_LINE_COUNT_VECTOR),
        "page_count": 8,
        "sample_count": 835,
    }
    assert all(value is False for value in stored_run["safety"].values())
    for name in ("attempt.json", "ocr_result.json", "run_manifest.json"):
        assert (output / name).stat().st_mode & 0o777 == 0o444

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="resume and retry"):
        runner.run_authenticated_vietocr_all_line_v3(tmp_path, capability)
    assert execution["calls"] == 1


def test_failed_execution_leaves_permanent_attempt_only(monkeypatch, tmp_path, project_root):
    capability, _execution = _prepare_run(monkeypatch, tmp_path, project_root)
    calls = {"execute": 0}

    def fail(*_args):
        calls["execute"] += 1
        raise RuntimeError("injected GPU failure")

    monkeypatch.setattr(runner, "_execute_model", fail)
    with pytest.raises(RuntimeError, match="injected GPU failure"):
        runner.run_authenticated_vietocr_all_line_v3(tmp_path, capability)

    output = tmp_path / runner.RUN_ROOT
    assert (output / "attempt.json").is_file()
    assert not (output / "ocr_result.json").exists()
    assert not (output / "run_manifest.json").exists()
    assert calls["execute"] == 1

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="resume and retry"):
        runner.run_authenticated_vietocr_all_line_v3(tmp_path, capability)
    assert calls["execute"] == 1


def test_existing_fixed_output_blocks_before_preflight(monkeypatch, tmp_path):
    (tmp_path / runner.RUN_ROOT).mkdir(parents=True)
    monkeypatch.setattr(
        runner,
        "_git",
        lambda _root, *args: (
            f"{tmp_path.resolve()}\n".encode()
            if args == ("rev-parse", "--show-toplevel")
            else pytest.fail(f"unexpected Git call: {args!r}")
        ),
    )
    monkeypatch.setattr(
        runner, "_git_binding", lambda _root: pytest.fail("preflight must not start")
    )
    monkeypatch.setattr(
        runner,
        "assert_authenticated_vietocr_all_line_freeze_project_root_v3",
        lambda *_args: None,
    )

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="resume and retry"):
        runner.run_authenticated_vietocr_all_line_v3(tmp_path, object())


def test_nested_fake_project_root_is_rejected_before_model_or_output(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    nested = repository / "nested-fake-root"
    (nested / "output/development").mkdir(parents=True)
    calls = {"git_binding": 0, "model": 0, "output": 0}

    monkeypatch.setattr(
        runner,
        "_git",
        lambda root, *args: (
            f"{repository.resolve()}\n".encode()
            if root == nested.resolve() and args == ("rev-parse", "--show-toplevel")
            else pytest.fail(f"unexpected Git call: {root!r} {args!r}")
        ),
    )

    def forbidden(name):
        def invoke(*_args, **_kwargs):
            calls[name] += 1
            pytest.fail(f"{name} must not run for a nested fake project root")

        return invoke

    monkeypatch.setattr(runner, "_git_binding", forbidden("git_binding"))
    monkeypatch.setattr(runner, "_execute_model", forbidden("model"))
    monkeypatch.setattr(runner, "_create_attempt_root", forbidden("output"))

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="exactly equal"):
        runner.run_authenticated_vietocr_all_line_v3(nested, object())

    assert calls == {"git_binding": 0, "model": 0, "output": 0}
    assert not (nested / runner.RUN_ROOT).exists()


def test_dirty_git_is_rejected_before_tracked_reads(monkeypatch, tmp_path):
    monkeypatch.setattr(runner, "_git", lambda _root, *_args: b" M source.py\n")
    monkeypatch.setattr(
        runner, "_tracked_ref", lambda *_args: pytest.fail("tracked files must not be read")
    )

    with pytest.raises(runner.VietOCRAllLineRunnerV3Error, match="clean Git worktree"):
        runner._git_binding(tmp_path)
