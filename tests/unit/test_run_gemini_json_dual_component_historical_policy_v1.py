from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _runner(name: str):
    path = ROOT / "scripts/experiments/run_gemini_json_dual_component_accounting_family_v1.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner


def _strict_trial(runner, row: dict, ordinal: int) -> dict:
    oracle_trial = row["oracle_trial"]
    if oracle_trial["status"] == "NOT_OBSERVED_IN_BOUND_SOURCE_SCOPE":
        return {
            "candidate_count": 0,
            "candidates": [],
            "document_ordinal": ordinal,
            "mappings": [],
            "source_sha256": row["source_sha256"],
            "status": runner.NOT_OBSERVED,
        }
    mappings = [
        {
            "report_norm_id": mapping["report_norm_id"],
            "values": [
                {"coefficient": value["normalized_value"]} for value in mapping["source_values"]
            ],
        }
        for mapping in oracle_trial["verified_mappings"]
    ]
    physical_pages = {
        value["page_sequence"]
        for mapping in oracle_trial["verified_mappings"]
        for value in mapping["source_values"]
    }
    assert len(physical_pages) == 1
    candidate = {"mappings": mappings, "physical_page": physical_pages.pop()}
    return {
        "candidate_count": 1,
        "candidates": [candidate],
        "document_ordinal": ordinal,
        "mappings": mappings,
        "source_sha256": row["source_sha256"],
        "status": runner.READY,
    }


def test_strict_release_preserves_exact_page_rnid_coefficient_comparison() -> None:
    runner = _runner("dual_component_policy_strict_v1")
    _, rows = runner._normalised_old_oracle_rows()
    trials = [_strict_trial(runner, row, ordinal) for ordinal, row in enumerate(rows, 1)]
    sources = [trial["source_sha256"] for trial in trials]
    pages = [f"gfpstorev1:json:{ordinal:064x}" for ordinal in range(1, 3)]

    comparator, rich, refs, receipt = runner._old_oracle_comparator_axis(
        policy=runner.STRICT_RELEASE,
        current_manifest_index_id="gjfccmiv1:index:" + "1" * 64,
        current_manifest_source_sha256s=sources,
        current_manifest_page_json_version_ids=pages,
        current_candidate_source_sha256s=[
            trial["source_sha256"] for trial in trials if trial["candidates"]
        ],
        current_replay_source_sha256s=[
            trial["source_sha256"] for trial in trials if trial["candidates"]
        ],
        trials=trials,
    )

    assert len(refs) == 2
    assert len(comparator) == len(rich) == 16
    assert sum(item["old_status"] == "READY" for item in comparator) == 8
    assert all(item["exact"] for item in comparator)
    assert receipt["policy"] == runner.STRICT_RELEASE
    assert receipt["disposition"] == runner.EXACT_HISTORICAL_COMPARISON


def test_disjoint_expansion_authenticates_oracles_and_materializes_no_fake_join() -> None:
    runner = _runner("dual_component_policy_expansion_v1")
    sources = ["e" * 64, "f" * 64]
    pages = ["gfpstorev1:json:" + "1" * 64, "gfpstorev1:json:" + "2" * 64]
    trials = [
        {
            "candidate_count": 0,
            "candidates": [],
            "document_ordinal": ordinal,
            "mappings": [],
            "source_sha256": source,
            "status": runner.NOT_OBSERVED,
        }
        for ordinal, source in enumerate(sources, 1)
    ]

    comparator, rich, refs, receipt = runner._old_oracle_comparator_axis(
        policy=runner.DISJOINT_EXPANSION,
        current_manifest_index_id="gjfccmiv1:index:" + "2" * 64,
        current_manifest_source_sha256s=sources,
        current_manifest_page_json_version_ids=pages,
        current_candidate_source_sha256s=[],
        current_replay_source_sha256s=[],
        trials=trials,
    )

    assert comparator == rich == []
    assert receipt["comparison_axis"] == []
    assert receipt["corpus_relation"]["overlap_count"] == 0
    assert receipt["oracle_authentication"]["refs"] == refs
    assert receipt["oracle_authentication"]["source_count"] == 16
    assert receipt["disposition"] == runner.NOT_APPLICABLE_DISJOINT_CORPUS


def test_disjoint_expansion_rejects_partial_old_oracle_overlap() -> None:
    runner = _runner("dual_component_policy_partial_v1")
    _, rows = runner._normalised_old_oracle_rows()
    sources = [rows[0]["source_sha256"], "f" * 64]
    trials = [
        {
            "candidate_count": 0,
            "candidates": [],
            "document_ordinal": ordinal,
            "mappings": [],
            "source_sha256": source,
            "status": runner.NOT_OBSERVED,
        }
        for ordinal, source in enumerate(sources, 1)
    ]

    with pytest.raises(ValueError, match="overlap only partially"):
        runner._old_oracle_comparator_axis(
            policy=runner.DISJOINT_EXPANSION,
            current_manifest_index_id="gjfccmiv1:index:" + "3" * 64,
            current_manifest_source_sha256s=sources,
            current_manifest_page_json_version_ids=["gfpstorev1:json:" + "4" * 64],
            current_candidate_source_sha256s=[],
            current_replay_source_sha256s=[],
            trials=trials,
        )


def test_official_run_cannot_select_disjoint_expansion_policy() -> None:
    runner = _runner("dual_component_policy_official_v1")

    with pytest.raises(
        runner.RunGeminiJsonDualComponentAccountingFamilyV1Error,
        match="requires STRICT_RELEASE",
    ):
        runner.run(
            SimpleNamespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="OFFICIAL",
            )
        )
