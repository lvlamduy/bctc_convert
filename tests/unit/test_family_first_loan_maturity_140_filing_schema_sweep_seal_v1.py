from __future__ import annotations

import copy
import hashlib
import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/E-0171-family-first-loan-maturity-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seal_digest(seal: dict[str, object]) -> str:
    material = dict(seal)
    material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_loan_maturity_140_filing_seal_is_hash_bound_closed_and_tamper_sensitive() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    assert seal["seal_id"] == "e0171:seal:" + _seal_digest(seal)
    assert seal["state"] == "COMPLETE"
    assert seal["git_commit"] == "047711b2e8e7e7eccdfea8a6c16126d350912aad"
    assert seal["sweep_id"] == (
        "lm140v1:sweep:3bfe3d4c0c412b013686ca553a690fc2a2a3246ac332736cac488e9e64da029c"
    )

    metrics = seal["metrics"]
    assert set(metrics) == {
        "additional_source_population_count",
        "additional_source_population_money_cell_count",
        "additional_source_population_row_count",
        "bank_mapped_record_counts",
        "branch_variant_trial_counts",
        "computed_unprinted_core_identity_count",
        "continuation_page_count",
        "document_count",
        "explicit_parent_branch_variant_trial_counts",
        "hosted_gemma4_challenged_full_page_count",
        "hosted_gemma4_conflict_cell_count",
        "hosted_gemma4_control_cell_count",
        "hosted_gemma4_stateless_request_count",
        "implied_parent_branch_variant_trial_counts",
        "mapped_core_record_count",
        "mapped_margin_record_count",
        "mapped_money_cell_count",
        "mapped_parent_716_or_752_record_count",
        "mapped_record_count",
        "minimal_pair_unique_trial_count",
        "numeric_exact_trial_count",
        "observed_accounting_equation_count",
        "observed_accounting_equation_counts",
        "owner_mode_trial_counts",
        "percentage_child_cell_count",
        "percentage_total_control_cell_count",
        "period_mode_trial_counts",
        "raw_resolved_total_variant_divergence_count",
        "raw_total_variant_trial_counts",
        "shortlisted_page_hydration_count",
        "structure_unique_trial_count",
        "total_variant_trial_counts",
        "typed_lane_axis_trial_counts",
        "unit_scope_trial_counts",
        "unresolved_trial_count",
        "verified_trial_count",
        "visible_dash_zero_cell_count",
    }
    assert {
        key: metrics[key]
        for key in (
            "document_count",
            "verified_trial_count",
            "unresolved_trial_count",
            "mapped_core_record_count",
            "mapped_margin_record_count",
            "mapped_record_count",
            "mapped_money_cell_count",
            "percentage_child_cell_count",
            "percentage_total_control_cell_count",
            "observed_accounting_equation_count",
            "visible_dash_zero_cell_count",
        )
    } == {
        "document_count": 140,
        "verified_trial_count": 140,
        "unresolved_trial_count": 0,
        "mapped_core_record_count": 420,
        "mapped_margin_record_count": 18,
        "mapped_record_count": 438,
        "mapped_money_cell_count": 876,
        "percentage_child_cell_count": 108,
        "percentage_total_control_cell_count": 36,
        "observed_accounting_equation_count": 352,
        "visible_dash_zero_cell_count": 8,
    }
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 140
    assert sum(item["mapped_record_count"] for item in seal["bank_summary"]) == 438
    assert metrics["bank_mapped_record_counts"] == {
        item["bank"]: item["mapped_record_count"] for item in seal["bank_summary"]
    }

    tampered = copy.deepcopy(seal)
    tampered["metrics"]["mapped_record_count"] = 439
    assert "e0171:seal:" + _seal_digest(tampered) != seal["seal_id"]


def test_loan_maturity_seal_tracked_refs_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for reference in seal[group].values():
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]


def test_loan_maturity_restored_snapshot_refs_match_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    references = list(seal["restored_snapshot_refs"].values())
    paths = [ROOT / reference["path"] for reference in references]
    if not any(path.exists() for path in paths):
        return
    assert all(path.exists() for path in paths)
    for path, reference in zip(paths, references, strict=True):
        assert path.stat().st_size == reference["size_bytes"]
        assert _sha(path) == reference["sha256"]
    assert seal["authority"]["public_exact_replay_requires_restored_snapshot"] is True
    assert seal["authority"]["bare_git_checkout_sufficient_for_public_exact_replay"] is False


def test_formal_loan_maturity_result_matches_seal_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    reference = seal["formal_result_ref"]
    path = ROOT / reference["path"]
    if not path.exists():
        return
    result = json.loads(path.read_text(encoding="utf-8"))
    assert path.stat().st_size == reference["size_bytes"]
    assert _sha(path) == reference["sha256"]
    assert stat.S_IMODE(path.stat().st_mode) == int(reference["mode"], 8)
    assert set(result) == {
        "authority",
        "claim_boundary",
        "format_version",
        "inputs",
        "metrics",
        "state",
        "sweep_id",
        "trials",
        "variant_divergences",
    }
    assert result["state"] == "COMPLETE"
    assert result["sweep_id"] == seal["sweep_id"]
    assert result["metrics"] == seal["metrics"]
    assert len(result["trials"]) == 140
    assert {trial["status"] for trial in result["trials"]} == {"VERIFIED_BY_CODEX"}
    assert (
        result["inputs"]["hosted_gemma4_challenger"]
        == seal["input_refs"]["hosted_gemma4_challenger"]
    )
