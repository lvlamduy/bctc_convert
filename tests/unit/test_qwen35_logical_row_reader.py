from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.ocr import qwen35_logical_row_reader
from bctc_ai.ocr.qwen35_logical_row_reader import (
    Qwen35LogicalRowReaderError,
    load_qwen35_logical_row_config,
    parse_qwen_transcription,
)


def test_qwen35_config_is_reference_blind_and_uses_explicit_triton_map(project_root):
    config, authorization, path, authorization_path = load_qwen35_logical_row_config(
        project_root,
        Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
    )

    assert path.is_file()
    assert authorization_path.is_file()
    assert authorization["triggered"] is True
    assert authorization["decision"] == "RUN_QWEN_SAME_REQUEST"
    assert authorization["reference_labels_ids_values_or_periods_available_to_reader"] is False
    assert config["request"]["sha256"] == (
        "ad4c1a9fecf9686249a9c4eea2a5b6a2a903fc4716536e5804c481facc217781"
    )
    assert config["quantization"]["dynamic_exclusion_keys"] == [
        "lm_head",
        "model.language_model.embed_tokens",
        "-:.*attn.*",
        "-:.*shared_expert.*",
        "-:.*mtp.*",
        "-:.*visual.*",
    ]
    modules = config["device_map"]["modules"]
    assert len(modules) == 68
    assert all(modules[f"model.language_model.layers.{index}"] == "cuda:0" for index in range(38))
    assert all(modules[f"model.language_model.layers.{index}"] == "cpu" for index in range(38, 64))
    assert set(modules.values()) == {"cuda:0", "cpu"}
    assert config["runtime_compatibility"]["native_shell_probe_without_weights"] == (
        "PASS_192_GPTQ_MLP_MODULES_META_PLACEHOLDERS"
    )
    assert config["runtime_compatibility"]["native_shell_quantized_placeholder_device"] == ("meta")
    assert config["runtime_compatibility"]["native_shell_quantized_placeholder_buffer_count"] == 768
    assert config["runtime_compatibility"]["native_shell_quantized_placeholder_buffer_names"] == [
        "g_idx",
        "qweight",
        "qzeros",
        "scales",
    ]
    assert config["output"] == {
        "directory": "output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader",
        "seal_path": "docs/experiments/E-0036-qwen-output-seal.json",
        "exact_files": ["ocr_result.json", "run_manifest.json"],
        "required_seal_state": "QWEN_OUTPUT_HASH_SEALED_BEFORE_REVIEW_ACCESS",
        "sealer": {
            "path": "src/bctc_ai/evaluation/qwen35_logical_row_output_seal.py",
            "sha256": "d4726772431cae3695d89985d919e1e3d30ab36611d4adc7bdfb826c534ccaff",
            "size_bytes": 39500,
        },
        "capture_script": {
            "path": "scripts/experiments/capture_e0036_qwen_output_seal.py",
            "sha256": "87f249368058f8c61a242e6c61d78a71e7995fa69ccd2d267f3d11f012bd1ccc",
            "size_bytes": 1439,
        },
    }
    assert not any(config["safety"].values())


def test_qwen35_freezes_transformers_torch_fallback_before_gptq_kernel_patch():
    source = inspect.getsource(qwen35_logical_row_reader._run_qwen35_logical_row_reader_impl)

    assert source.index("from transformers.models.qwen3_5 import modeling_qwen3_5") < source.index(
        "from gptqmodel import GPTQModel"
    )


def test_qwen35_meta_quant_placeholders_are_scoped_and_restored():
    class FakeDevice:
        def __init__(self, torch, value):
            self._torch = torch
            self.type = value.type if isinstance(value, FakeDevice) else str(value)
            self._previous = None

        def __enter__(self):
            self._previous = self._torch.current_device
            self._torch.current_device = self.type
            return self

        def __exit__(self, *_exc):
            self._torch.current_device = self._previous

    class FakeTorch:
        def __init__(self):
            self.current_device = "cpu"

        def device(self, value):
            return FakeDevice(self, value)

    fake_torch = FakeTorch()

    class FakeTensor:
        def __init__(self):
            self.device = SimpleNamespace(type=fake_torch.current_device)

        def numel(self):
            return 4

        def element_size(self):
            return 4

    class DummyQuantLinear:
        def __init__(self):
            self.qweight = FakeTensor()

        def list_buffers(self):
            return [self.qweight]

        def named_buffers(self, *, recurse):
            assert recurse is False
            return [("qweight", self.qweight)]

        def to(self, target):
            self.qweight.device = SimpleNamespace(type=fake_torch.device(target).type)
            return self

    class Parent:
        def __init__(self):
            self.slot = object()
            self.extra = object()

    parent = Parent()

    def create_quant_module(*, name, module):
        replacement = DummyQuantLinear().to(fake_torch.device("cpu"))
        setattr(module, name, replacement)

    model_utils = SimpleNamespace(
        create_quant_module=create_quant_module,
        recurse_getattr=lambda module, name: getattr(module, name),
    )
    original_to = DummyQuantLinear.to

    with qwen35_logical_row_reader._meta_quantized_placeholder_initialization(
        fake_torch,
        DummyQuantLinear,
        model_utils,
        expected_module_count=1,
        expected_buffer_names=frozenset({"qweight"}),
    ) as evidence:
        model_utils.create_quant_module(name="slot", module=parent)
        assert parent.slot.qweight.device.type == "meta"
        assert model_utils.create_quant_module is not create_quant_module
        with pytest.raises(
            qwen35_logical_row_reader.Qwen35LogicalRowReaderError,
            match="too many GPTQ meta quant placeholders",
        ):
            model_utils.create_quant_module(name="extra", module=parent)
        assert not isinstance(parent.extra, DummyQuantLinear)

    assert model_utils.create_quant_module is create_quant_module
    assert DummyQuantLinear.to is original_to
    assert evidence == {
        "mechanism": "GPTQ_META_AFTER_CPU_SOURCE_SHAPE_VALIDATION",
        "module_count": 1,
        "buffer_count": 1,
        "buffer_names": ["qweight"],
        "nominal_buffer_bytes": 16,
        "placeholder_device": "meta",
        "hooks_restored_after_load": True,
    }


def test_qwen35_authorization_is_minimal_but_derived_from_sealed_evaluation(project_root):
    authorization_path = (
        project_root / "docs/experiments/E-0036-qwen-reference-blind-inference-authorization.json"
    )
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    reviewed_evaluation = (
        project_root / "docs/experiments/E-0036-mbb-cdkt-reviewed-reader-evaluation.json"
    )

    assert authorization["derived_from_reviewed_evaluation_sha256"] == sha256_file(
        reviewed_evaluation
    )
    serialized = json.dumps(authorization, ensure_ascii=False).casefold()
    for forbidden in (
        "reportnormid",
        "reviewed_item_id",
        "pdf_label",
        "canonical_name",
        "raw_value",
        "normalized_value",
        "period_map_id",
    ):
        assert forbidden not in serialized
    reader_source = inspect.getsource(qwen35_logical_row_reader)
    assert "E-0036-mbb-cdkt-reviewed-reader-evaluation.json" not in reader_source


def test_qwen35_config_rejects_human_review_access(monkeypatch, project_root):
    source = Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml")
    original_loads = qwen35_logical_row_reader.tomllib.loads

    def load_with_drift(value):
        payload = original_loads(value)
        payload["safety"]["human_review_access"] = True
        return payload

    monkeypatch.setattr(qwen35_logical_row_reader.tomllib, "loads", load_with_drift)

    with pytest.raises(Qwen35LogicalRowReaderError, match="configuration drifted"):
        load_qwen35_logical_row_config(project_root, source)


def test_qwen35_parser_accepts_bounded_transcription_and_preserves_raw():
    parsed = parse_qwen_transcription(
        "  Các khoản lãi, phí phải thu  ",
        generated_token_count=12,
        maximum_new_tokens=96,
        terminated_by_eos=True,
        maximum_nonempty_lines=4,
        maximum_output_characters=512,
    )

    assert parsed["status"] == "PARSED_SEMANTIC_PROPOSAL_ONLY"
    assert parsed["proposal_text"] == "Các khoản lãi, phí phải thu"
    assert parsed["generated_token_count"] == 12


def test_qwen35_parser_rejects_prompt_echo():
    prompt = (
        "Transcribe exactly the visible Vietnamese text in this crop. "
        "Do not correct spelling. Return only the transcription."
    )
    parsed = parse_qwen_transcription(
        "Transcribe exactly the visible Vietnamese text in this crop.",
        generated_token_count=12,
        maximum_new_tokens=96,
        terminated_by_eos=True,
        maximum_nonempty_lines=4,
        maximum_output_characters=512,
        prompt=prompt,
    )

    assert parsed["status"] == "REJECT_PROMPT_ECHO"
    assert parsed["proposal_text"] == ""


@pytest.mark.parametrize(
    "raw",
    [
        "</tool_call> Các khoản phải thu",
        "<tool_response>Các khoản phải thu</tool_response>",
        "The transcription is: Các khoản phải thu",
    ],
)
def test_qwen35_parser_rejects_control_serialization_and_preamble(raw):
    parsed = parse_qwen_transcription(
        raw,
        generated_token_count=12,
        maximum_new_tokens=96,
        terminated_by_eos=True,
        maximum_nonempty_lines=4,
        maximum_output_characters=512,
    )

    assert parsed["status"] == "REJECT_REASONING_OR_SERIALIZATION"
    assert parsed["proposal_text"] == ""


@pytest.mark.parametrize(
    ("raw", "tokens", "terminated", "expected"),
    [
        ("<think>đoán nhãn</think>", 8, True, "REJECT_REASONING_OR_SERIALIZATION"),
        (
            "vốn vốn vốn vốn vốn vốn vốn vốn vốn vốn vốn vốn",
            12,
            True,
            "REJECT_PATHOLOGICAL_REPETITION",
        ),
        ("Nhãn bị cắt", 96, False, "REJECT_TOKEN_BUDGET_EXHAUSTED"),
        ("123 - 456", 4, True, "REJECT_NON_TEXTUAL_OUTPUT"),
    ],
)
def test_qwen35_parser_rejects_untrusted_generation(raw, tokens, terminated, expected):
    parsed = parse_qwen_transcription(
        raw,
        generated_token_count=tokens,
        maximum_new_tokens=96,
        terminated_by_eos=terminated,
        maximum_nonempty_lines=4,
        maximum_output_characters=512,
    )

    assert parsed["status"] == expected
    assert parsed["proposal_text"] == ""


def test_qwen35_device_map_rejects_disk_or_single_device():
    with pytest.raises(Qwen35LogicalRowReaderError, match="device map violates"):
        qwen35_logical_row_reader._normalize_device_map({"": "disk"})
    with pytest.raises(Qwen35LogicalRowReaderError, match="device map violates"):
        qwen35_logical_row_reader._normalize_device_map({"": "cuda:0"})


def test_qwen35_formal_runner_requires_one_shot_worker(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("BCTC_QWEN35_ONE_SHOT_WORKER", raising=False)

    with pytest.raises(Qwen35LogicalRowReaderError, match="one-shot worker"):
        qwen35_logical_row_reader.run_qwen35_logical_row_reader(
            tmp_path,
            request_path=Path("request.json"),
            output_directory=Path("output"),
            model_cache_root=tmp_path,
        )


def test_qwen35_formal_runner_rejects_noncanonical_output(monkeypatch, project_root: Path):
    monkeypatch.setattr(qwen35_logical_row_reader, "_git", lambda *_args: "")
    monkeypatch.setattr(
        qwen35_logical_row_reader,
        "load_qwen35_logical_row_config",
        lambda *_args: (
            {
                "output": {
                    "directory": (
                        "output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader"
                    )
                },
                "hard_watchdog": {
                    "path": "scripts/models/qwen35_inference_watchdog.py",
                    "sha256": "f99056c24acaa7df3bf230b30a45d094ec4d7a764e3cd415fde538988d6adcc0",
                    "size_bytes": 1309,
                },
                "request": {
                    "path": "output/calibration/e0036-mbb-cdkt-semantic-label-readers/request.json",
                    "sha256": "ad4c1a9fecf9686249a9c4eea2a5b6a2a903fc4716536e5804c481facc217781",
                },
            },
            {},
            project_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml",
            project_root
            / "docs/experiments/E-0036-qwen-reference-blind-inference-authorization.json",
        ),
    )
    with pytest.raises(Qwen35LogicalRowReaderError, match="canonical lexical path"):
        qwen35_logical_row_reader._run_qwen35_logical_row_reader_impl(
            project_root,
            request_path=Path(
                "output/calibration/e0036-mbb-cdkt-semantic-label-readers/request.json"
            ),
            output_directory=Path(
                "output/calibration/e0036-mbb-cdkt-semantic-label-readers/qwen-reader-alternate"
            ),
            model_cache_root=project_root,
        )


def test_qwen35_control_token_range_is_rejected_after_terminal_eos_removal():
    assert qwen35_logical_row_reader._forbidden_generated_control_tokens(
        [100, 248044, 248058, 248067, 300000],
        minimum=248045,
        maximum=248076,
    ) == [248058, 248067]


def test_qwen35_external_watchdog_starts_and_stops(project_root: Path):
    process = qwen35_logical_row_reader._start_hard_watchdog(
        project_root / "scripts/models/qwen35_inference_watchdog.py",
        timeout_seconds=5,
        ready_timeout_seconds=2,
    )

    qwen35_logical_row_reader._stop_hard_watchdog(process)


def test_qwen35_external_watchdog_hard_kills_timed_out_target(project_root: Path):
    target = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    watchdog = subprocess.Popen(
        [
            sys.executable,
            str(project_root / "scripts/models/qwen35_inference_watchdog.py"),
            "--pid",
            str(target.pid),
            "--timeout-seconds",
            "1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert watchdog.stdout is not None
        assert watchdog.stdout.readline().strip() == "READY"
        assert watchdog.wait(timeout=5) == 124
        assert target.wait(timeout=5) < 0
    finally:
        if watchdog.poll() is None:
            watchdog.kill()
        if target.poll() is None:
            target.kill()


def test_qwen35_weight_index_requires_full_explicit_map_coverage(tmp_path: Path):
    model_directory = tmp_path / "model"
    model_directory.mkdir()
    (model_directory / "model.safetensors.index.json").write_text(
        json.dumps(
            {
                "weight_map": {
                    "model.language_model.layers.0.mlp.gate_proj.qweight": "shard-1",
                    "mtp.fc.weight": "shard-1",
                }
            }
        ),
        encoding="utf-8",
    )
    config = {
        "device_map": {
            "modules": {"model.language_model.layers.0": "cuda:0"},
            "expected_weight_index_tensor_count": 2,
            "expected_device_map_covered_tensor_count": 1,
            "expected_excluded_auxiliary_mtp_tensor_count": 1,
        }
    }

    assert qwen35_logical_row_reader._verify_weight_map_coverage(model_directory, config) == {
        "weight_index_tensor_count": 2,
        "device_map_covered_tensor_count": 1,
        "excluded_auxiliary_mtp_tensor_count": 1,
    }

    config["device_map"]["modules"] = {"model.visual": "cuda:0"}
    with pytest.raises(Qwen35LogicalRowReaderError, match="not fully covered"):
        qwen35_logical_row_reader._verify_weight_map_coverage(model_directory, config)


def test_qwen35_loader_rejects_alternate_config_even_with_identical_bytes(project_root, tmp_path):
    alternate = tmp_path / "qwen.toml"
    alternate.write_bytes(
        (project_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml").read_bytes()
    )

    with pytest.raises(Qwen35LogicalRowReaderError, match="canonical lexical path"):
        load_qwen35_logical_row_config(project_root, alternate)


def test_qwen35_loader_rejects_symlinked_canonical_config(project_root, tmp_path):
    fake_root = tmp_path / "project"
    config = fake_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"
    config.parent.mkdir(parents=True)
    config.symlink_to(project_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml")

    with pytest.raises(Qwen35LogicalRowReaderError, match="symlink component"):
        load_qwen35_logical_row_config(
            fake_root,
            Path("config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"),
        )


def test_qwen35_model_verifier_rejects_symlinked_artifact_parent(tmp_path: Path):
    model = tmp_path / "model"
    real = tmp_path / "real"
    model.mkdir()
    real.mkdir()
    artifact = real / "weights.bin"
    artifact.write_bytes(b"pinned")
    (model / "nested").symlink_to(real, target_is_directory=True)
    config = {
        "required_artifact_bytes": len(b"pinned"),
        "artifacts": {
            "weights": {
                "path": "nested/weights.bin",
                "size_bytes": len(b"pinned"),
                "sha256": sha256_file(artifact),
            }
        },
    }

    with pytest.raises(Qwen35LogicalRowReaderError, match="symlink component"):
        qwen35_logical_row_reader._verify_model(model, config)


def test_qwen35_model_and_overlay_verifiers_reject_special_files(tmp_path: Path):
    model = tmp_path / "model"
    model.mkdir()
    artifact = model / "weights.bin"
    artifact.write_bytes(b"pinned")
    os.mkfifo(model / "unregistered.pipe")
    config = {
        "required_artifact_bytes": len(b"pinned"),
        "artifacts": {
            "weights": {
                "path": artifact.name,
                "size_bytes": len(b"pinned"),
                "sha256": sha256_file(artifact),
            }
        },
    }

    with pytest.raises(Qwen35LogicalRowReaderError, match="non-regular filesystem entry"):
        qwen35_logical_row_reader._verify_model(model, config)

    overlay = tmp_path / "overlay"
    overlay.mkdir()
    (overlay / "module.py").write_text("value = 1\n", encoding="utf-8")
    os.mkfifo(overlay / "unregistered.pipe")
    with pytest.raises(Qwen35LogicalRowReaderError, match="non-regular filesystem entry"):
        qwen35_logical_row_reader._exact_tree_identity(overlay)


def test_qwen35_model_verifier_rejects_registered_fifo_without_blocking(tmp_path: Path):
    model = tmp_path / "model"
    model.mkdir()
    os.mkfifo(model / "weights.bin")
    config = {
        "required_artifact_bytes": 0,
        "artifacts": {
            "weights": {
                "path": "weights.bin",
                "size_bytes": 0,
                "sha256": "0" * 64,
            }
        },
    }

    with pytest.raises(Qwen35LogicalRowReaderError, match="not a regular file"):
        qwen35_logical_row_reader._verify_model(model, config)
