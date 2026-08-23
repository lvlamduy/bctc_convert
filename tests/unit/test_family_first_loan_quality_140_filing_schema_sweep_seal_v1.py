from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0169-family-first-loan-quality-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_loan_quality_140_filing_seal_is_hash_bound_and_closed() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    material = dict(seal)
    identity = material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    assert identity == "e0169:seal:" + hashlib.sha256(canonical).hexdigest()
    assert seal["metrics"] == {
        "document_count": 140,
        "excluded_footnote_hosted_gemma4_bound_crop_count": 4,
        "hosted_gemma4_consensus_challenger_hit_count": 2,
        "layout_mode_trial_counts": {
            "HORIZONTAL_TYPED_PERIOD_LANES": 122,
            "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS": 18,
        },
        "mapped_core_grade_record_count": 700,
        "mapped_margin_record_count": 27,
        "mapped_record_count": 727,
        "margin_presentation_mode_trial_counts": {
            "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": 4,
            "INCLUDED_IN_747_VIA_5746": 6,
            "NOT_OBSERVED_DO_NOT_SYNTHESIZE": 113,
            "STANDALONE_AFTER_FIVE_GRADES": 17,
        },
        "numeric_exact_trial_count": 140,
        "structure_unique_trial_count": 140,
        "typed_lane_axis_trial_counts": {
            "MONEY,MONEY": 136,
            "MONEY,PERCENT,MONEY,PERCENT": 4,
        },
        "unresolved_trial_count": 0,
        "verified_trial_count": 140,
    }
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 140
    assert sum(item["mapped_record_count"] for item in seal["bank_summary"]) == 727


def test_loan_quality_seal_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for reference in seal[group].values():
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]


def test_formal_loan_quality_result_matches_seal_when_available() -> None:
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
