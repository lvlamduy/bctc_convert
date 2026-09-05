from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import (
    compile_gemini_json_multitable_hierarchical_family_specs_v1,
)

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "scripts/experiments/run_gemini_json_service_activity_accounting_family_v1.py"
SPEC = importlib.util.spec_from_file_location("run_service_activity_family_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _compiled_specs():
    paths = (
        "config/families/tm-service-activity-topology-v1.json",
        "config/families/tm-service-activity-evaluation-v1.json",
        "config/families/tm-service-activity-schema-binding-v1.json",
    )
    return compile_gemini_json_multitable_hierarchical_family_specs_v1(
        *[json.loads((ROOT / path).read_bytes()) for path in paths]
    )


def _sweep(*, coefficient: int = 7, mapping_id: str = "mapping-a"):
    return {
        "family_id": runner.FAMILY_ID,
        "trials": [
            {
                "mappings": [
                    {
                        "item_mapping_id": mapping_id,
                        "report_norm_id": 1158,
                        "role": "INCOME_PAYMENT",
                        "row_id": "r2",
                        "source_refs": [{"label_exact": "Dịch vụ thanh toán", "row_id": "r2"}],
                        "state": "SOURCE_VISIBLE_DIRECT_ROW",
                        "unit": "MILLION_VND",
                        "values": [
                            {
                                "coefficient": coefficient,
                                "source_text": str(coefficient),
                                "state": "RAW_SIGNED_INTEGER",
                            },
                            {
                                "coefficient": 6,
                                "source_text": "6",
                                "state": "RAW_SIGNED_INTEGER",
                            },
                        ],
                    }
                ],
                "reasons": [],
                "source_logical_name": "vietstock_bctc/BANK/2025/report.pdf",
                "source_sha256": "a" * 64,
                "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
            }
        ],
    }


def _pin_baseline(monkeypatch, tmp_path, sweep, *, expected_delta_count=0):
    payload = json.dumps(sweep, ensure_ascii=False, sort_keys=True).encode()
    baseline = tmp_path / "baseline.json"
    baseline.write_bytes(payload)
    monkeypatch.setattr(
        runner, "PINNED_STRICT_REGRESSION_SWEEP_SHA256", sha256(payload).hexdigest()
    )
    monkeypatch.setattr(runner, "PINNED_STRICT_REGRESSION_SWEEP_SIZE_BYTES", len(payload))
    monkeypatch.setattr(
        runner,
        "PINNED_STRICT_REGRESSION_SEMANTIC_DELTA_COUNT",
        expected_delta_count,
    )
    return baseline


def test_strict_regression_ignores_only_content_derived_mapping_id(monkeypatch, tmp_path):
    baseline = _pin_baseline(monkeypatch, tmp_path, _sweep())
    receipt = runner._strict_regression_receipt(
        sweep=_sweep(mapping_id="new-spec-derived-id"), baseline_path=baseline
    )
    assert receipt["disposition"] == (
        "EXACT_SOURCE_STATUS_REASON_AXIS_WITH_AUTHENTICATED_EVIDENCE_SAFE_"
        "SEMANTIC_MAPPING_DELTAS"
    )
    assert receipt["source_count"] == 1
    assert receipt["mapping_semantic_delta_count"] == 0
    assert receipt["source_observation_contract"]["status"] == "PASS"
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="candidate axis is invalid",
    ):
        runner._strict_regression_receipt(sweep=_sweep(coefficient=8), baseline_path=baseline)


def _authenticated_candidate_sweep(*, mapping_state: str) -> dict:
    sweep = _sweep()
    trial = sweep["trials"][0]
    mapping = trial["mappings"][0]
    mapping["state"] = mapping_state
    mapping["source_refs"] = [
        {
            "label_exact": "Dịch vụ thanh toán",
            "locator": {
                "page_json_version_id": "gfpstorev1:json:" + "b" * 64,
                "section_id": "s1",
                "table_id": "t1",
            },
            "row_id": "r2",
        }
    ]
    candidate_id = "gjmthfcv1:candidate:" + "c" * 64
    trial.update(
        {
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": candidate_id,
                    "component_regions": [
                        {
                            "page_json_version_id": "gfpstorev1:json:" + "b" * 64,
                            "section_id": "s1",
                            "table_id": "t1",
                        }
                    ],
                    "mappings": copy.deepcopy(trial["mappings"]),
                    "reasons": [],
                    "status": "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY",
                }
            ],
            "document_ordinal": 1,
            "selected_candidate_id": candidate_id,
        }
    )
    return sweep


def test_strict_semantic_delta_receipt_is_content_derived_and_tamper_evident(
    monkeypatch, tmp_path
):
    baseline_sweep = _authenticated_candidate_sweep(
        mapping_state="SOURCE_VISIBLE_DIRECT_ROW"
    )
    current_sweep = _authenticated_candidate_sweep(
        mapping_state="SOURCE_OBSERVED_RESEALED_ROW"
    )
    baseline = _pin_baseline(
        monkeypatch,
        tmp_path,
        baseline_sweep,
        expected_delta_count=1,
    )
    receipt = runner._strict_regression_receipt(
        sweep=current_sweep,
        baseline_path=baseline,
    )
    assert receipt["mapping_semantic_delta_count"] == 1
    delta = receipt["mapping_semantic_delta_axis"][0]
    assert delta["reason_axis"] == ["SEMANTIC_VALUES_STABLE_PROVENANCE_RESEALED"]
    assert runner.validate_service_activity_strict_regression_receipt_v1(
        receipt,
        sweep=current_sweep,
        baseline_path=baseline,
    ) == receipt

    tampered = copy.deepcopy(receipt)
    tampered["mapping_semantic_delta_axis"][0]["mapping_changes"][0][
        "reason"
    ] = "UNAUTHENTICATED_CHANGE"
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="receipt drifted",
    ):
        runner.validate_service_activity_strict_regression_receipt_v1(
            tampered,
            sweep=current_sweep,
            baseline_path=baseline,
        )


def test_strict_regression_requires_pinned_regular_bytes(monkeypatch, tmp_path):
    baseline = _pin_baseline(monkeypatch, tmp_path, _sweep())
    monkeypatch.setattr(runner, "PINNED_STRICT_REGRESSION_SWEEP_SHA256", "0" * 64)
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="bytes drifted",
    ):
        runner._strict_regression_receipt(sweep=_sweep(), baseline_path=baseline)
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="requires --strict-regression-sweep",
    ):
        runner._strict_regression_receipt(sweep=_sweep(), baseline_path=None)


def test_semantic_axis_rejects_wrong_family_and_duplicate_sources():
    wrong = _sweep()
    wrong["family_id"] = "OTHER_ACTIVITY"
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="not Family 30",
    ):
        runner._semantic_trial_axis(wrong)
    duplicate = _sweep()
    duplicate["trials"].append(duplicate["trials"][0])
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="source axis is invalid",
    ):
        runner._semantic_trial_axis(duplicate)


def test_disjoint_policy_authenticates_oracles_and_proves_zero_overlap():
    source_sha256 = "f" * 64
    comparator, refs, receipt = runner._historical_comparator_axis(
        policy=runner.DISJOINT_EXPANSION,
        current_manifest_index_id="gjfccmiv1:index:" + "e" * 64,
        current_manifest_source_sha256s=[source_sha256],
        current_manifest_page_json_version_ids=["gfpstorev1:json:" + "d" * 64],
        current_candidate_source_sha256s=[],
        current_replay_source_sha256s=[],
        trials=[{"source_sha256": source_sha256}],
        compiled_specs=_compiled_specs(),
    )
    assert comparator == []
    assert [ref["expected_trial_count"] for ref in refs] == [8, 8]
    assert receipt["disposition"] == runner.NOT_APPLICABLE_DISJOINT_CORPUS
    assert receipt["corpus_relation"]["overlap_count"] == 0
    assert receipt["oracle_authentication"]["source_count"] == 16


def test_disjoint_receipt_requires_zero_intersection_and_empty_comparator():
    audit = {
        "axes": {"historical_comparator": []},
        "historical_comparator_policy_receipt": {
            "comparison_axis": [],
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
    }
    runner._assert_policy_receipt(audit=audit, policy=runner.DISJOINT_EXPANSION)
    audit["historical_comparator_policy_receipt"]["corpus_relation"]["overlap_count"] = 1
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="not exactly disjoint",
    ):
        runner._assert_policy_receipt(audit=audit, policy=runner.DISJOINT_EXPANSION)


def test_run_mode_gate_rejects_official_expansion_and_baseline_on_expansion(tmp_path):
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="OFFICIAL Family 30 run requires STRICT_RELEASE",
    ):
        runner.run(
            argparse.Namespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="OFFICIAL",
                strict_regression_sweep=None,
            )
        )
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="cannot claim a strict regression sweep",
    ):
        runner.run(
            argparse.Namespace(
                historical_comparator_policy=runner.DISJOINT_EXPANSION,
                run_kind="EXPERIMENTAL",
                strict_regression_sweep=tmp_path / "baseline.json",
            )
        )


def test_implementation_receipt_and_family_shape_are_exact():
    refs = runner._implementation_refs()
    paths = [ref["path"] for ref in refs]
    assert refs[0]["path"] == (
        "scripts/experiments/run_gemini_json_service_activity_accounting_family_v1.py"
    )
    assert len(paths) == len(set(paths))
    assert set(paths) >= {
        "data/registered/gemini_json_service_activity_source_repairs_v1.json",
        "src/bctc_ai/evaluation/gemini_json_service_activity_family_v1.py",
        "src/bctc_ai/evaluation/source_observation_mapping_contract_v1.py",
    }
    assert runner._family_id(_compiled_specs()) == runner.FAMILY_ID


def test_internal_source_replay_uses_generic_specs_bound_to_exact_adapter():
    topology = json.loads(runner.TOPOLOGY_SPEC_PATH.read_bytes())
    evaluation = json.loads(runner.EVALUATION_SPEC_PATH.read_bytes())
    schema = json.loads(runner.SCHEMA_BINDING_SPEC_PATH.read_bytes())
    generic = _compiled_specs()
    family = runner.bind_gemini_json_service_activity_source_repair_artifact_v1(
        generic,
        json.loads(runner.SOURCE_REPAIR_PATH.read_bytes()),
    )
    assert family["query_policy"] == generic["query_policy"]
    recovered = runner._generic_source_replay_specs_v1(
        topology=topology,
        evaluation=evaluation,
        schema=schema,
        family_compiled=family,
    )
    assert recovered == generic
    assert "service_activity_source_repair_overlay" not in recovered

    family["service_activity_source_repair_spec_sha256"] = "0" * 64
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="generic and adapter declarative specs differ",
    ):
        runner._generic_source_replay_specs_v1(
            topology=topology,
            evaluation=evaluation,
            schema=schema,
            family_compiled=family,
        )


def test_current_corpus_gate_and_source_pdf_root_fail_closed(tmp_path):
    runner._assert_current_corpus(
        {"documents": [{"relative_path": "vietstock_bctc/BANK/2025/report.pdf"}]}
    )
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "vietstock_bctc/BANK/2024/report.pdf"}]}
        )
    with pytest.raises(
        runner.RunGeminiJsonServiceActivityAccountingFamilyV1Error,
        match="source-PDF root is unavailable",
    ):
        runner._authenticate_source_repair_images_v1(
            repairs=[],
            source_pdf_root=tmp_path / "missing",
        )
