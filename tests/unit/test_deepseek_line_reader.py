from __future__ import annotations

import pytest

from bctc_ai.ocr.deepseek_line_reader import (
    DeepSeekLineReaderError,
    install_generation_token_cap,
    load_deepseek_line_config,
    parse_free_ocr_output,
    validate_reference_blind_line_request,
)


def _request():
    return {
        "format_version": 1,
        "experiment_id": "E-0024",
        "state": "READY_FOR_REFERENCE_BLIND_LINE_INFERENCE",
        "dataset_role": "LOGIC_DEVELOPMENT_AND_CALIBRATION",
        "evidence_role": "INDEPENDENT_VIETNAMESE_SEMANTIC_PROPOSAL_ONLY",
        "git_commit": "deadbeef",
        "git_dirty": False,
        "crop_manifest": {"path": "manifest.json", "sha256": "a" * 64},
        "reference_text_available_to_reader": False,
        "sample_count": 1,
        "samples": [
            {
                "sample_id": "mbb-p10-title",
                "category": "TITLE",
                "crop_path": "crop.png",
                "crop_sha256": "b" * 64,
            }
        ],
    }


def test_config_locks_offline_free_ocr_and_forbidden_authority(project_root):
    config, base, path = load_deepseek_line_config(
        project_root, project_root / "config/models/deepseek-ocr2-line-v1.toml"
    )

    assert path == project_root / "config/models/deepseek-ocr2-line-v1.toml"
    assert config["inference"] == {
        "prompt": "<image>\nFree OCR.",
        "base_size": 1024,
        "image_size": 768,
        "crop_mode": False,
        "attention_implementation": "eager",
        "network_permitted": False,
        "reference_text_available_to_decoder": False,
        "target_policy": "FROZEN_PP_OCRV6_LINE_TITLE_OR_LOGICAL_ROW_CROPS_ONLY",
        "maximum_nonempty_output_lines": 4,
    }
    assert all(value is False for value in config["safety"].values())
    assert base["model"]["repo_id"] == "deepseek-ai/DeepSeek-OCR-2"


def test_config_cannot_escape_project_root(project_root, tmp_path):
    external = tmp_path / "external.toml"
    external.write_text("version = 1\n", encoding="utf-8")

    with pytest.raises(DeepSeekLineReaderError, match="escapes"):
        load_deepseek_line_config(project_root, external)


def test_v2_config_preserves_aspect_and_bounds_generation_before_inference(project_root):
    config, _, _ = load_deepseek_line_config(
        project_root, project_root / "config/models/deepseek-ocr2-line-v2.toml"
    )

    assert config["version"] == 2
    assert config["inference"]["crop_mode"] is True
    assert config["inference"]["aspect_preservation"] == "OFFICIAL_IMAGEOPS_PAD"
    assert config["inference"]["maximum_new_tokens"] == 128
    assert config["inference"]["upstream_requested_maximum_new_tokens"] == 8192
    assert config["inference"]["maximum_output_characters"] == 512


def test_request_is_reference_blind_and_allowlisted():
    assert validate_reference_blind_line_request(_request()) == _request()["samples"]


@pytest.mark.parametrize("field", ["expected_text", "reference", "ppocr_text", "schema_id"])
def test_request_rejects_reference_baseline_or_schema_fields(field):
    request = _request()
    request["samples"][0][field] = "forbidden"

    with pytest.raises(DeepSeekLineReaderError, match="forbidden"):
        validate_reference_blind_line_request(request)


def test_request_rejects_unsafe_sample_identity():
    request = _request()
    request["samples"][0]["sample_id"] = "../../escape"

    with pytest.raises(DeepSeekLineReaderError, match="unsafe"):
        validate_reference_blind_line_request(request)


def test_free_ocr_parser_preserves_one_line_and_joins_bounded_wrapped_row():
    single = parse_free_ocr_output(
        "  BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT  ", maximum_nonempty_lines=4
    )
    wrapped = parse_free_ocr_output(
        "Các khoản phải thu\ntừ khách hàng và đối tác", maximum_nonempty_lines=4
    )

    assert single == {
        "status": "PARSED_SEMANTIC_PROPOSAL_ONLY",
        "proposal_text": "BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT",
        "nonempty_line_count": 1,
    }
    assert wrapped["proposal_text"] == "Các khoản phải thu từ khách hàng và đối tác"
    assert wrapped["nonempty_line_count"] == 2


def test_free_ocr_parser_rejects_output_character_budget_before_semantic_use():
    parsed = parse_free_ocr_output(
        "Tài sản " * 100,
        maximum_nonempty_lines=4,
        maximum_output_characters=64,
    )

    assert parsed["status"] == "REJECT_OUTPUT_CHARACTER_BUDGET_EXCEEDED"
    assert parsed["proposal_text"] == ""


def test_generation_cap_fails_closed_if_upstream_budget_drifts():
    class Model:
        def __init__(self):
            self.calls = []

        def generate(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return kwargs["max_new_tokens"]

    model = Model()
    install_generation_token_cap(
        model,
        upstream_requested_maximum_new_tokens=8192,
        maximum_new_tokens=128,
    )

    assert model.generate("input", max_new_tokens=8192) == 128
    assert model.calls[0][1]["max_new_tokens"] == 128
    with pytest.raises(DeepSeekLineReaderError, match="upstream generation budget changed"):
        model.generate("input", max_new_tokens=4096)


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        ("", "REJECT_EMPTY_OUTPUT"),
        ("<|ref|>text<|/ref|><|det|>[[1,2,3,4]]<|/det|>", "REJECT_DOCUMENT"),
        ("| Cột 1 | Cột 2 |", "REJECT_DOCUMENT"),
        ("```text\nTài sản\n```", "REJECT_DOCUMENT"),
        ("1.234.567", "REJECT_NON_TEXTUAL"),
        ("a\nb\nc\nd\ne", "REJECT_TOO_MANY"),
    ],
)
def test_free_ocr_parser_rejects_empty_layout_numeric_or_unbounded_output(raw, status):
    parsed = parse_free_ocr_output(raw, maximum_nonempty_lines=4)

    assert parsed["status"].startswith(status)
    assert parsed["proposal_text"] == ""
