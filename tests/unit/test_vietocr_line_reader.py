from __future__ import annotations

import pytest

from bctc_ai.ocr import vietocr_line_reader
from bctc_ai.ocr.vietocr_line_reader import (
    VietOCRLineReaderError,
    validate_reference_blind_request,
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
        "crop_manifest": {"path": "manifest.json", "sha256": "abc"},
        "reference_text_available_to_reader": False,
        "sample_count": 1,
        "samples": [
            {
                "sample_id": "sample-1",
                "category": "TITLE",
                "crop_path": "crop.png",
                "crop_sha256": "def",
            }
        ],
    }


def test_accepts_exact_reference_blind_allowlist():
    samples = validate_reference_blind_request(_request())

    assert samples == [
        {
            "sample_id": "sample-1",
            "category": "TITLE",
            "crop_path": "crop.png",
            "crop_sha256": "def",
        }
    ]


@pytest.mark.parametrize("field", ["expected_text", "reference", "ppocr_text"])
def test_rejects_any_reference_or_baseline_field(field):
    request = _request()
    request["samples"][0][field] = "forbidden"

    with pytest.raises(VietOCRLineReaderError, match="forbidden"):
        validate_reference_blind_request(request)


def test_rejects_reference_availability_flag():
    request = _request()
    request["reference_text_available_to_reader"] = True

    with pytest.raises(VietOCRLineReaderError, match="identity or role"):
        validate_reference_blind_request(request)


def test_generic_request_denominator_is_not_fixed_to_logical_row_batch():
    request = _request()
    request["samples"] = [
        {
            "sample_id": f"sample-{index:03d}",
            "category": "LOGICAL_ROW_LABEL",
            "crop_path": f"crop-{index:03d}.png",
            "crop_sha256": f"sha-{index:03d}",
        }
        for index in range(106)
    ]
    request["sample_count"] = len(request["samples"])

    assert len(validate_reference_blind_request(request)) == 106


def test_generic_line_reader_accepts_pinned_rtx4090_config(project_root):
    config = vietocr_line_reader._load_config(
        project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    )

    assert config["version"] == 2
    assert config["runtime_compatibility"]["minimum_compute_capability"] == [8, 9]
    assert config["runtime_compatibility"]["historical_blackwell_runtime_claimed"] is False
    assert config["inference"]["reference_text_available_to_decoder"] is False
    assert all(value is False for value in config["safety"].values())


def test_generic_line_reader_rejects_rtx4090_authority_drift(tmp_path, project_root):
    source = project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    drifted = tmp_path / "vietocr-rtx4090.toml"
    drifted.write_text(
        source.read_text(encoding="utf-8").replace(
            "mapping_authority = false", "mapping_authority = true"
        ),
        encoding="utf-8",
    )

    with pytest.raises(VietOCRLineReaderError, match="drifted|forbidden|unsafe"):
        vietocr_line_reader._load_config(drifted)


def test_generic_line_reader_rejects_rtx4090_package_registry_drift(tmp_path, project_root):
    source = project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    drifted = tmp_path / "vietocr-rtx4090.toml"
    drifted.write_text(
        source.read_text(encoding="utf-8").replace('torch = "2.12.0+cu130"', 'torch = "0.0.0"'),
        encoding="utf-8",
    )

    with pytest.raises(VietOCRLineReaderError, match="runtime policy drifted"):
        vietocr_line_reader._load_config(drifted)


@pytest.mark.parametrize("capability", [(8, 9), (9, 0), (12, 0)])
def test_rtx4090_config_accepts_capability_at_or_above_pinned_minimum(capability, project_root):
    config = vietocr_line_reader._load_config(
        project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    )

    vietocr_line_reader._validate_cuda_capability(config, capability)


def test_rtx4090_config_rejects_capability_below_pinned_minimum(project_root):
    config = vietocr_line_reader._load_config(
        project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    )

    with pytest.raises(VietOCRLineReaderError, match="RTX 4090-compatible"):
        vietocr_line_reader._validate_cuda_capability(config, (8, 8))


@pytest.mark.parametrize(
    ("python_major_minor", "cuda_runtime", "message"),
    [
        ("3.10", "13.0", "Python runtime"),
        ("3.11", "12.8", "CUDA runtime"),
    ],
)
def test_rtx4090_config_rejects_runtime_identity_drift(
    python_major_minor, cuda_runtime, message, project_root
):
    config = vietocr_line_reader._load_config(
        project_root / "config/models/vietocr-0.3.13-rtx4090.toml"
    )

    with pytest.raises(VietOCRLineReaderError, match=message):
        vietocr_line_reader._validate_runtime_identity(
            config,
            python_major_minor=python_major_minor,
            cuda_runtime=cuda_runtime,
        )


def test_legacy_config_preserves_exact_blackwell_capability_gate(project_root):
    config = vietocr_line_reader._load_config(project_root / "config/models/vietocr-0.3.13.toml")

    vietocr_line_reader._validate_cuda_capability(config, (12, 0))
    with pytest.raises(VietOCRLineReaderError, match="verified Blackwell"):
        vietocr_line_reader._validate_cuda_capability(config, (12, 1))


def test_formal_runner_rejects_dirty_tree_before_loading_request(tmp_path, monkeypatch):
    monkeypatch.setattr(vietocr_line_reader, "_git", lambda *_args: " M tracked-file")

    with pytest.raises(VietOCRLineReaderError, match="clean Git worktree"):
        vietocr_line_reader.run_vietocr_line_reader(
            tmp_path,
            request_path=tmp_path / "absent-request.json",
            output_directory=tmp_path / "output",
            runtime_root=tmp_path / "runtime",
        )
