from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import (
    run_gemini_json_operating_expense_accounting_family_v1 as runner,
)


def _audit() -> dict:
    material = {
        "axis_counts": {
            "equations": 1,
            "mappings": 1,
            "source_repairs": 1,
            "trials": 1,
            "unit_corroborations": 0,
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
        "source_observation_contract": {"violation_count": 0},
        "source_repair_application": {"violation_count": 0},
        "source_repair_authentication": [{"repair_id": "repair"}],
        "spec_refs": {},
        "sweep_id": "sweep",
        "sweep_output": "/dev/shm/family36.json",
    }
    return {
        **material,
        "audit_id": "gjoefauditv1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: value for key, value in audit.items() if key != "audit_id"}
    audit["audit_id"] = "gjoefauditv1:audit:" + canonical_json_sha256_v1(material)


def test_runner_pins_shared_engine_and_runner() -> None:
    runner._assert_shared_pins_v1()


def test_runner_rejects_non_disjoint_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="outside the current reporting scope",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )


def test_source_repair_authentication_requires_real_pdf_root(tmp_path: Path) -> None:
    repair = {
        "crop_evidence": {
            "bbox_pixels_xyxy": [0, 0, 1, 1],
            "pixel_height": 1,
            "pixel_width": 1,
            "rgb_sha256": "1" * 64,
        },
        "locator": {"physical_page": 1},
        "render": {},
        "source": {
            "source_logical_name": "missing.pdf",
            "source_sha256": "2" * 64,
            "source_size_bytes": 1,
        },
    }
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="source path is unavailable",
    ):
        runner._authenticate_source_repairs_v1(
            repairs=[repair], source_pdf_root=tmp_path
        )


def test_source_repair_application_is_exactly_once_and_corpus_scoped() -> None:
    repair = {
        "repair_id": "gjoefav1:source-repair:" + "1" * 64,
        "source": {"source_sha256": "2" * 64},
    }
    receipt = runner._source_repair_application_receipt_v1(
        index={"documents": [{"source_sha256": "2" * 64}]},
        compiled_specs={
            "operating_expense_source_repairs": [repair],
            "operating_expense_source_repair_spec_sha256": "3" * 64,
        },
        trials=[
            {
                "candidates": [
                    {
                        "closure_receipt": {
                            "operating_expense_adapter_receipt": {
                                "source_repair_receipts": [{"repair": repair}]
                            }
                        }
                    }
                ]
            }
        ],
    )
    assert receipt["violation_count"] == 0
    assert receipt["expected_repair_ids"] == receipt["applied_repair_ids"]

    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="application gate failed",
    ):
        runner._source_repair_application_receipt_v1(
            index={"documents": [{"source_sha256": "2" * 64}]},
            compiled_specs={
                "operating_expense_source_repairs": [repair],
                "operating_expense_source_repair_spec_sha256": "3" * 64,
            },
            trials=[],
        )


def test_audit_rejects_contract_violation_and_identity_tamper() -> None:
    assert runner.validate_operating_expense_experimental_audit_v1(_audit())

    invented = copy.deepcopy(_audit())
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_operating_expense_experimental_audit_v1(invented)

    missing_repair = copy.deepcopy(_audit())
    missing_repair["source_repair_application"]["violation_count"] = 1
    _reseal(missing_repair)
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit content is invalid",
    ):
        runner.validate_operating_expense_experimental_audit_v1(missing_repair)

    tampered = _audit()
    tampered["sweep_id"] = "tampered"
    with pytest.raises(
        runner.RunGeminiJsonOperatingExpenseV1Error,
        match="audit identity drifted",
    ):
        runner.validate_operating_expense_experimental_audit_v1(tampered)
