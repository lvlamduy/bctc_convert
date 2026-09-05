from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import (
    run_gemini_json_interest_income_accounting_family_v1 as runner,
)


def _audit() -> dict:
    material = {
        "axis_counts": {
            "cross_fragment_same_role_parent_equations": 2,
            "equations": 1,
            "mappings": 1,
            "one_sided_continuations": 1,
            "period_normalizations": 2,
            "query_recoveries": 1,
            "source_repairs": 30,
            "trials": 1,
            "unit_corroborations": 58,
        },
        "axis_sha256": {},
        "family_id": runner.FAMILY_ID,
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": {
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        "indexed_query_receipt": {},
        "source_repair_application": {
            "applied_count": 30,
            "applied_repair_ids_sha256": "a" * 64,
            "applied_unique_count": 30,
            "expected_count": 30,
            "expected_repair_ids_sha256": "a" * 64,
            "overlay_id": "gjiifav1:overlay:" + "b" * 64,
        },
        "source_observation_contract": {"violation_count": 0},
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/dev/shm/family28.json",
    }
    return {
        **material,
        "audit_id": "gjiifauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = "gjiifauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_pins_shared_engine_and_runner() -> None:
    runner._assert_shared_pins_v1()


def test_runner_rejects_non_disjoint_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus({"documents": [{"relative_path": "bank/2024/report.pdf"}]})


def test_current_corpus_gate_rejects_a_current_year_subset() -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="requires the authenticated full271 corpus",
    ):
        runner._assert_current_corpus(
            {
                "corpus_manifest_index_id": runner.PINNED_CURRENT_CORPUS_INDEX_ID,
                "documents": [{"relative_path": "bank/2025/report.pdf"}],
                "summary": {"document_count": 1, "page_count": 1},
            }
        )


def test_source_repair_authentication_requires_real_pdf_root(tmp_path: Path) -> None:
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="source-PDF root is unavailable",
    ):
        runner._authenticate_source_repair_images_v1(
            repairs=[], source_pdf_root=tmp_path / "missing"
        )


def test_audit_rejects_missing_repairs_and_source_invention() -> None:
    assert runner.validate_interest_income_experimental_audit_v1(_audit())

    missing_cross_fragment_equation = copy.deepcopy(_audit())
    missing_cross_fragment_equation["axis_counts"][
        "cross_fragment_same_role_parent_equations"
    ] = 1
    _reseal(missing_cross_fragment_equation)
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_income_experimental_audit_v1(
            missing_cross_fragment_equation
        )

    missing_repair = copy.deepcopy(_audit())
    missing_repair["axis_counts"]["source_repairs"] = 29
    _reseal(missing_repair)
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_income_experimental_audit_v1(missing_repair)

    duplicated_repair = copy.deepcopy(_audit())
    duplicated_repair["source_repair_application"]["applied_unique_count"] = 29
    _reseal(duplicated_repair)
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_income_experimental_audit_v1(duplicated_repair)

    wrong_repair_axis = copy.deepcopy(_audit())
    wrong_repair_axis["source_repair_application"]["applied_repair_ids_sha256"] = "c" * 64
    _reseal(wrong_repair_axis)
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_income_experimental_audit_v1(wrong_repair_axis)

    invented = copy.deepcopy(_audit())
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit content is invalid",
    ):
        runner.validate_interest_income_experimental_audit_v1(invented)


def test_audit_identity_tamper_fails_closed() -> None:
    audit = _audit()
    audit["sweep_id"] = "tampered"
    with pytest.raises(
        runner.RunGeminiJsonInterestIncomeV1Error,
        match="audit identity drifted",
    ):
        runner.validate_interest_income_experimental_audit_v1(audit)


def test_audit_builder_binds_the_exact_registered_repair_id_axis() -> None:
    repair_ids = [f"gjiifav1:repair:{index:064x}" for index in range(30)]
    repair_receipts = [{"repair_id": repair_id} for repair_id in repair_ids]
    trials = [
        {
            "candidates": [
                {
                    "closure_receipt": {
                        "cross_fragment_same_role_parent_equation_receipts": [{}, {}],
                        "equations": [],
                        "interest_income_adapter_receipt": {
                            "one_sided_continuation_receipts": [{}],
                            "period_normalization_receipts": [{}, {}],
                            "source_repair_receipts": repair_receipts,
                            "unit_corroboration_receipts": [{} for _ in range(58)],
                        },
                    },
                    "mappings": [],
                }
            ]
        }
    ]
    audit = runner.build_interest_income_experimental_audit_v1(
        sweep={"sweep_id": "sweep"},
        output=Path("/dev/shm/family28.json"),
        indexed={"query_receipt": {}},
        trials=trials,
        historical_receipt={
            "corpus_relation": {"overlap_count": 0},
            "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
            "policy": runner.DISJOINT_EXPANSION,
        },
        observation_contract={"violation_count": 0},
        query_recovery_receipts=[{}],
        source_repair_overlay={
            "overlay_id": "gjiifav1:overlay:" + "b" * 64,
            "repairs": [{"repair_id": repair_id} for repair_id in repair_ids],
        },
        spec_refs={},
    )

    assert runner.validate_interest_income_experimental_audit_v1(audit)
    application = audit["source_repair_application"]
    assert application["applied_repair_ids_sha256"] == application["expected_repair_ids_sha256"]
