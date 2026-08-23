from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0163-family-first-derivative-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_derivative_140_filing_seal_is_hash_bound_and_closed() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    material = dict(seal)
    identity = material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert identity == "e0163:seal:" + hashlib.sha256(canonical).hexdigest()
    assert seal["metrics"] == {
        "bounded_not_observed_count": 14,
        "document_count": 140,
        "numeric_challenger_rescue_count": 3,
        "unresolved_document_count": 0,
        "verified_document_count": 126,
        "verified_mapping_count": 1684,
    }
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 126
    assert sum(item["bounded_not_observed_count"] for item in seal["bank_summary"]) == 14
    assert len(seal["bounded_not_observed_filings"]) == 14
    assert all(item["bank"] == "VCB" for item in seal["bounded_not_observed_filings"])


def test_derivative_seal_tracked_input_and_implementation_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for reference in seal[group].values():
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]


def test_formal_result_matches_seal_when_local_artifact_is_available() -> None:
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
