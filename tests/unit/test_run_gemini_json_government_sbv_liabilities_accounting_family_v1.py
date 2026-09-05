from __future__ import annotations

import argparse
import copy
import importlib.util
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.storage.gemini_accounting_family_store_v1 import (
    GeminiAccountingFamilyStoreV1Error,
    _checked_source_replay_adapter_v1,
    _run_checked_source_replay_adapter_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT / "scripts/experiments/run_gemini_json_government_sbv_liabilities_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_government_sbv_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _receipt(*, policy: str = runner.DISJOINT_EXPANSION) -> dict:
    return {
        "comparison_axis": [],
        "corpus_relation": {"overlap_count": 0},
        "current_axis_validation": {
            "candidate_source_count": 0,
            "manifest_document_count": 2,
            "replay_source_count": 0,
            "selected_page_json_version_count": 3,
            "trial_source_count": 2,
        },
        "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
        "format_version": runner.HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
        "oracle_authentication": {
            "artifact_count": 2,
            "refs": [
                {
                    **reference,
                    "expected_trial_count": runner.PINNED_HISTORICAL_ORACLE_TRIAL_COUNT,
                }
                for reference in runner.PINNED_HISTORICAL_ORACLES
            ],
            "source_count": 16,
        },
        "policy": policy,
    }


def _sealed_audit() -> dict:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
        "query_recoveries": [],
        "source_repairs": [],
    }
    fields = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {name: canonical_json_sha256_v1(axis) for name, axis in axes.items()},
        "audit_metrics": {
            "equation_count": 0,
            "historical_comparator_exact_count": None,
            "mapping_count": 0,
            "source_repair_count": 0,
        },
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": _receipt(),
        "query_evidence_id": "fixture-query",
        "query_receipt": {
            "accepted_cluster_count": 0,
            "selected_document_count": 2,
            "selected_page_count": 3,
        },
        "selected_page_json_frontier_sha256": "a" * 64,
        "source_observation_contract": {
            "cell_count": 0,
            "derived_cell_count": 0,
            "format_version": "SOURCE_OBSERVATION_MAPPING_CONTRACT_AUDIT_V1",
            "mapping_count": 0,
            "partial_mapping_count": 0,
            "source_blank_cell_count": 0,
            "status": "PASS",
            "violation_count": 0,
            "violations": [],
        },
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_ref": {},
    }
    return {
        **fields,
        "audit_id": "gjgslfeav1:audit:" + canonical_json_sha256_v1(fields),
    }


def _reseal(audit: dict) -> None:
    material = {key: audit[key] for key in audit if key != "audit_id"}
    audit["audit_id"] = "gjgslfeav1:audit:" + canonical_json_sha256_v1(material)


def test_pinned_government_oracles_authenticate_and_have_unique_source_axis() -> None:
    compiled = runner.compile_gemini_json_government_sbv_liabilities_family_specs_v1(
        runner.generic._json(
            ROOT / "config/families/tm-government-sbv-liabilities-topology-v1.json"
        ),
        runner.generic._json(
            ROOT / "config/families/tm-government-sbv-liabilities-evaluation-v1.json"
        ),
        runner.generic._json(
            ROOT / "config/families/tm-government-sbv-liabilities-schema-binding-v1.json"
        ),
        runner.generic._json(
            ROOT
            / "data/registered/gemini_json_government_sbv_liabilities_source_repairs_v1.json"
        ),
    )
    refs, rows = runner._normalised_historical_oracle_rows(compiled_specs=compiled)
    assert refs == [
        {
            **reference,
            "expected_trial_count": runner.PINNED_HISTORICAL_ORACLE_TRIAL_COUNT,
        }
        for reference in runner.PINNED_HISTORICAL_ORACLES
    ]
    assert len(rows) == 16
    assert len({row["source_sha256"] for row in rows}) == 16
    assert [row["oracle_ref_index"] for row in rows] == [0] * 8 + [1] * 8


def test_disjoint_audit_receipt_validates_and_tamper_fails_closed() -> None:
    audit = _sealed_audit()
    assert runner.validate_government_sbv_liabilities_experimental_audit_content_v1(audit)

    tampered = copy.deepcopy(audit)
    tampered["historical_comparator_policy_receipt"]["corpus_relation"]["overlap_count"] = 1
    _reseal(tampered)
    with pytest.raises(
        runner.RunGeminiJsonGovernmentSbvLiabilitiesAccountingFamilyV1Error,
        match="disjoint comparator",
    ):
        runner.validate_government_sbv_liabilities_experimental_audit_content_v1(tampered)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("policy", "UNKNOWN"),
        ("oracle_ref_order", None),
        ("candidate_count", 1),
    ],
)
def test_policy_unknown_order_and_axis_count_tamper_fail_closed(field: str, value: object) -> None:
    audit = _sealed_audit()
    receipt = audit["historical_comparator_policy_receipt"]
    if field == "policy":
        receipt["policy"] = value
    elif field == "oracle_ref_order":
        receipt["oracle_authentication"]["refs"].reverse()
    else:
        receipt["current_axis_validation"]["candidate_source_count"] = value
    _reseal(audit)
    with pytest.raises(
        runner.RunGeminiJsonGovernmentSbvLiabilitiesAccountingFamilyV1Error,
        match="policy receipt",
    ):
        runner.validate_government_sbv_liabilities_experimental_audit_content_v1(audit)


def test_run_rejects_disjoint_official_before_reading_inputs() -> None:
    args = argparse.Namespace(
        historical_comparator_policy=runner.DISJOINT_EXPANSION,
        run_kind="OFFICIAL",
    )
    with pytest.raises(
        runner.RunGeminiJsonGovernmentSbvLiabilitiesAccountingFamilyV1Error,
        match="requires STRICT_RELEASE",
    ):
        runner.run(args)


def _patch_source_replay_fixture(monkeypatch: pytest.MonkeyPatch) -> tuple[dict, list[dict]]:
    region = {
        "document_ordinal": 1,
        "page_json_version_id": "page-1",
        "physical_page": 1,
        "section_id": "s1",
        "table_id": "t1",
    }
    indexed = {
        "accepted_clusters": [
            {"component_regions": [region], "document_ordinal": 1}
        ],
        "selected_page_axis": [],
    }
    trial = {"document_ordinal": 1, "fixture": "source-replayed"}
    monkeypatch.setattr(runner.generic, "_json", lambda _path: {"repairs": []})
    monkeypatch.setattr(
        runner,
        "bind_gemini_json_government_sbv_liabilities_source_repairs_v1",
        lambda *_args: {"family_compiled": True},
    )
    monkeypatch.setattr(
        runner,
        "query_selected_multitable_hierarchical_family_regions_v1",
        lambda *_args, **_kwargs: {"selected_page_axis": []},
    )
    monkeypatch.setattr(
        runner.generic,
        "_load_selected_pages_by_document",
        lambda *_args, **_kwargs: {1: {"page-1": {}}},
    )
    monkeypatch.setattr(
        runner,
        "adapt_gemini_json_government_sbv_liabilities_indexed_query_evidence_v1",
        lambda *_args, **_kwargs: (indexed, []),
    )
    monkeypatch.setattr(
        runner,
        "build_gemini_json_government_sbv_liabilities_region_query_receipt_v1",
        lambda _regions: {"query": "receipt"},
    )
    monkeypatch.setattr(
        runner,
        "evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1",
        lambda **_kwargs: {"candidate": "evaluated"},
    )
    monkeypatch.setattr(
        runner,
        "validate_gemini_json_government_sbv_liabilities_family_candidate_replay_v1",
        lambda candidate, **_kwargs: candidate,
    )
    monkeypatch.setattr(
        runner.generic,
        "_trials",
        lambda **_kwargs: [trial],
    )
    return indexed, [trial]


def test_source_replay_hook_is_byte_bound_and_rebuilds_exact_trials(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    indexed, trials = _patch_source_replay_fixture(monkeypatch)
    runner_ref = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    implementation_refs = [runner_ref]
    checked, checked_ref = _checked_source_replay_adapter_v1(
        runner.replay_government_sbv_liabilities_trials_from_source_v1,
        adapter_ref=runner_ref,
        implementation_refs=implementation_refs,
    )
    assert checked is runner.replay_government_sbv_liabilities_trials_from_source_v1
    assert checked_ref == runner_ref
    _run_checked_source_replay_adapter_v1(
        checked,
        adapter_ref=runner_ref,
        implementation_refs=implementation_refs,
        source_page_database=tmp_path / "source.sqlite3",
        selected_page_json_version_ids=["page-1"],
        compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
        indexed_query_evidence=indexed,
        expected_trials=trials,
    )

    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="different trial axis",
    ):
        _run_checked_source_replay_adapter_v1(
            checked,
            adapter_ref=runner_ref,
            implementation_refs=implementation_refs,
            source_page_database=tmp_path / "source.sqlite3",
            selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
            indexed_query_evidence=indexed,
            expected_trials=[{"document_ordinal": 1, "fixture": "tampered"}],
        )


def test_source_replay_hook_ref_drift_and_exception_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    indexed, trials = _patch_source_replay_fixture(monkeypatch)
    runner_ref = runner.generic._file_ref(RUNNER_PATH, root=ROOT)
    drifted_ref = {**runner_ref, "sha256": "0" * 64}
    with pytest.raises(
        GeminiAccountingFamilyStoreV1Error,
        match="does not authenticate",
    ):
        _checked_source_replay_adapter_v1(
            runner.replay_government_sbv_liabilities_trials_from_source_v1,
            adapter_ref=drifted_ref,
            implementation_refs=[drifted_ref],
        )

    monkeypatch.setattr(
        runner,
        "evaluate_gemini_json_government_sbv_liabilities_family_cluster_v1",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("fixture adapter failure")),
    )
    with pytest.raises(RuntimeError, match="fixture adapter failure"):
        _run_checked_source_replay_adapter_v1(
            runner.replay_government_sbv_liabilities_trials_from_source_v1,
            adapter_ref=runner_ref,
            implementation_refs=[runner_ref],
            source_page_database=tmp_path / "source.sqlite3",
            selected_page_json_version_ids=["page-1"],
            compiled_specs={"topology": {}, "evaluation": {}, "schema": {}},
            indexed_query_evidence=indexed,
            expected_trials=trials,
        )
