from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

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
        project_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml",
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
    assert not any(config["safety"].values())


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
    source = project_root / "config/models/qwen35-27b-gptq-int4-rtx4090-v1.toml"
    original_load_toml = qwen35_logical_row_reader._load_toml

    def load_with_drift(path, label):
        payload = original_load_toml(path, label)
        if label == "Qwen config":
            payload["safety"]["human_review_access"] = True
        return payload

    monkeypatch.setattr(qwen35_logical_row_reader, "_load_toml", load_with_drift)

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
