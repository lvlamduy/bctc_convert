from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts/experiments/run_gemini_json_interest_rate_risk_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_interest_rate_risk_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_parser_accepts_external_effective_frontier_root(tmp_path: Path) -> None:
    frontier = tmp_path / "effective.json"
    repair_root = tmp_path / "repair-root"
    args = runner._parser().parse_args(
        [
            "--corpus-index",
            str(tmp_path / "index.json"),
            "--artifact-root",
            str(tmp_path / "corpus"),
            "--effective-page-frontier",
            str(frontier),
            "--effective-page-artifact-root",
            str(repair_root),
            "--topology-spec",
            str(tmp_path / "topology.json"),
            "--evaluation-spec",
            str(tmp_path / "evaluation.json"),
            "--schema-binding-spec",
            str(tmp_path / "schema.json"),
            "--results-database",
            str(tmp_path / "results.sqlite3"),
            "--run-kind",
            "EXPERIMENTAL",
            "--output",
            str(tmp_path / "sweep.json"),
        ]
    )
    assert args.effective_page_frontier == frontier
    assert args.effective_page_artifact_root == repair_root


def test_release_pins_require_exact_family49_effective_frontier(monkeypatch) -> None:
    monkeypatch.setattr(
        runner,
        "canonical_json_sha256_v1",
        lambda _value: runner.PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256,
    )
    sweep = {
        "corpus_manifest_index_id": runner.PINNED_CORPUS_MANIFEST_INDEX_ID,
        "effective_page_frontier": {
            "effective_page_frontier_id": runner.PINNED_EFFECTIVE_PAGE_FRONTIER_ID
        },
        "indexed_query_evidence": {"query_receipt": copy.deepcopy(runner.PINNED_QUERY_RECEIPT)},
        "metrics": copy.deepcopy(runner.PINNED_RELEASE_METRICS),
    }
    audit = {
        "audit_metrics": copy.deepcopy(runner.PINNED_AUDIT_METRICS),
        "axis_counts": copy.deepcopy(runner.PINNED_AXIS_COUNTS),
        "axis_sha256": copy.deepcopy(runner.PINNED_AXIS_SHA256),
    }
    runner._assert_release_pins(sweep=sweep, audit=audit, selected_ids=[])

    tampered = copy.deepcopy(sweep)
    tampered["effective_page_frontier"]["effective_page_frontier_id"] = (
        "gjfepfv1:frontier:" + "0" * 64
    )
    with pytest.raises(
        runner.RunGeminiJsonInterestRateRiskFamilyV1Error,
        match="release pins drifted",
    ):
        runner._assert_release_pins(sweep=tampered, audit=audit, selected_ids=[])
