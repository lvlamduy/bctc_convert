from __future__ import annotations

import tomllib
from pathlib import Path

from bctc_ai.core.hashing import sha256_file


def test_vietocr_runtime_manifest_has_exact_official_artifacts(project_root: Path):
    path = project_root / "config/models/vietocr-0.3.13.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8"))

    assert config["status"] == "CALIBRATION_ONLY_VIETNAMESE_SEMANTIC_LINE_PROPOSAL"
    assert config["inference"]["network_permitted"] is False
    assert config["inference"]["reference_text_available_to_decoder"] is False
    assert config["inference"]["cnn_pretrained_download"] is False
    assert config["artifacts"]["weights"] == {
        "path": "artifacts/vgg_transformer.pth",
        "url": "https://vocr.vn/data/vietocr/vgg_transformer.pth",
        "size_bytes": 151815373,
        "sha256": "380512193a8b6cbf6fad80deacdc9b6939d10d473d199892fc6408d13775ea59",
    }
    assert config["safety"] and not any(config["safety"].values())


def test_local_vietocr_artifacts_match_manifest_when_present(project_root: Path):
    config = tomllib.loads(
        (project_root / "config/models/vietocr-0.3.13.toml").read_text(encoding="utf-8")
    )
    runtime_root = Path("/workspace/bctc-ai-runtime/vietocr-0.3.13")
    if not runtime_root.exists():
        return
    for record in config["artifacts"].values():
        path = runtime_root / record["path"]
        assert path.stat().st_size == record["size_bytes"]
        assert sha256_file(path) == record["sha256"]


def test_vietocr_seq2seq_runtime_manifest_has_exact_official_artifacts(project_root: Path):
    path = project_root / "config/models/vietocr-0.3.13-vgg-seq2seq-rtx4090.toml"
    config = tomllib.loads(path.read_text(encoding="utf-8"))

    assert config["model_name"] == "VietOCR VGG Seq2Seq"
    assert config["architecture"] == "vgg19_bn_seq2seq"
    assert config["artifacts"]["model_config"] == {
        "path": "artifacts/vgg-seq2seq.yml",
        "url": "https://vocr.vn/data/vietocr/config/vgg-seq2seq.yml",
        "size_bytes": 673,
        "sha256": "0160ba8d442ae96f4c6095b92ac3521c59b83ce6eda9fd5459e8628a5586c3e8",
    }
    assert config["artifacts"]["weights"] == {
        "path": "artifacts/vgg_seq2seq.pth",
        "url": "https://vocr.vn/data/vietocr/vgg_seq2seq.pth",
        "size_bytes": 89575371,
        "sha256": "0921503a41375a0584268e23ef3d414ea478a8fe8777865c7745d38f2d0bc5db",
    }
    assert config["safety"] and not any(config["safety"].values())
