from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0166-family-first-loan-industry-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_loan_industry_140_filing_seal_is_hash_bound_and_closed() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    material = dict(seal)
    identity = material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert identity == "e0166:seal:" + hashlib.sha256(canonical).hexdigest()
    assert seal["metrics"] == {
        "confirmed_absent_trial_count": 42,
        "document_count": 140,
        "hosted_gemma4_consensus_rescue_count": 1,
        "mapped_child_record_count": 1520,
        "numeric_exact_or_corroborated_trial_count": 98,
        "source_rounding_corroborated_trial_count": 1,
        "structure_unique_trial_count": 98,
        "verified_present_trial_count": 98,
    }
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 98
    assert sum(item["confirmed_absent_document_count"] for item in seal["bank_summary"]) == 42
    assert sum(item["mapped_child_record_count"] for item in seal["bank_summary"]) == 1520
    assert seal["numeric_rescue"]["ppocrv6_surface"] == "31.027.066"
    assert {
        seal["numeric_rescue"]["vietocr_surface"],
        seal["numeric_rescue"]["independent_pixel_surface"],
        seal["numeric_rescue"]["hosted_gemma4_surface"],
    } == {"31.027.068"}


def test_loan_industry_seal_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for reference in seal[group].values():
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]
    crop = ROOT / seal["numeric_rescue"]["crop_ref"]["path"]
    assert crop.stat().st_size == seal["numeric_rescue"]["crop_ref"]["size_bytes"]
    assert _sha(crop) == seal["numeric_rescue"]["crop_ref"]["sha256"]


def test_formal_loan_industry_result_matches_seal_when_available() -> None:
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
