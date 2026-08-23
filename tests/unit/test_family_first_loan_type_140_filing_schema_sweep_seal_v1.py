from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0164-family-first-loan-type-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_loan_type_140_filing_seal_is_hash_bound_and_closed() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    material = dict(seal)
    identity = material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert identity == "e0164:seal:" + hashlib.sha256(canonical).hexdigest()
    assert seal["metrics"] == {
        "document_count": 140,
        "mapped_child_record_count": 732,
        "numeric_exact_trial_count": 140,
        "structure_unique_trial_count": 140,
        "targeted_same_crop_ppocrv6_rescue_count": 2,
        "verified_trial_count": 140,
        "visible_pixel_dash_zero_count": 140,
    }
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 140
    assert sum(item["mapped_child_record_count"] for item in seal["bank_summary"]) == 732
    assert len(seal["targeted_numeric_rescues"]) == 2
    assert all(item["ppocrv6_raw_prediction"] == "2" for item in seal["targeted_numeric_rescues"])


def test_loan_type_seal_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for reference in seal[group].values():
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]


def test_formal_loan_type_result_matches_seal_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    reference = seal["formal_result_ref"]
    path = ROOT / reference["path"]
    if not path.exists():
        return
    result = json.loads(path.read_text(encoding="utf-8"))
    assert path.stat().st_size == reference["size_bytes"]
    assert _sha(path) == reference["sha256"]
    assert result["sweep_id"] == seal["sweep_id"]
    assert result["metrics"] == seal["metrics"]
