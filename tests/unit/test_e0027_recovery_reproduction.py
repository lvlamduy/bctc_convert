from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from bctc_ai.recovery.e0027_reproduction import canonicalize_ocr_input_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_canonical_ocr_changes_only_source_path_and_is_stable():
    payload = {
        "input_path": "/new/page.png",
        "rec_texts": ["Tiền mặt"],
        "rec_scores": [0.99],
    }

    encoded = canonicalize_ocr_input_path(payload, "/historical/page.png")
    restored = json.loads(encoded)

    assert payload["input_path"] == "/new/page.png"
    assert restored == {
        "input_path": "/historical/page.png",
        "rec_texts": ["Tiền mặt"],
        "rec_scores": [0.99],
    }
    assert encoded.endswith(b"\n")
    assert hashlib.sha256(encoded).hexdigest() == hashlib.sha256(
        canonicalize_ocr_input_path(payload, "/historical/page.png")
    ).hexdigest()


def test_recovery_config_never_claims_original_batch_recovered():
    config = yaml.safe_load(
        (PROJECT_ROOT / "config/recovery/e0027-reproduction-v1.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert config["recovery_id"] == "R-0001"
    assert config["acceptance"]["original_batch_manifest_recovered"] is False
    assert config["acceptance"]["canonical_ocr_pages_3_4_byte_exact"] is True
    assert config["acceptance"]["discovery_result_json_exact"] is True
    assert "must never claim" in config["claim_boundary"]
