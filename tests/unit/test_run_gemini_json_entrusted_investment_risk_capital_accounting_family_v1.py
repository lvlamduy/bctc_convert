from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    ROOT
    / "scripts/experiments/"
    "run_gemini_json_entrusted_investment_risk_capital_accounting_family_v1.py"
)
SPEC = importlib.util.spec_from_file_location("run_family24_v1", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _policy_receipt() -> dict:
    return {
        "comparison_axis": [],
        "corpus_relation": {"overlap_count": 0},
        "disposition": runner.NOT_APPLICABLE_DISJOINT_CORPUS,
        "format_version": runner.HISTORICAL_COMPARATOR_POLICY_FORMAT_VERSION,
        "policy": runner.DISJOINT_EXPANSION,
    }


def _observation_contract() -> dict:
    return {
        "cell_count": 0,
        "derived_cell_count": 0,
        "format_version": "SOURCE_OBSERVATION_MAPPING_CONTRACT_AUDIT_V1",
        "mapping_count": 0,
        "partial_mapping_count": 0,
        "source_blank_cell_count": 0,
        "status": "PASS",
        "violation_count": 0,
        "violations": [],
    }


def _audit() -> dict:
    axes = {
        "clusters": [],
        "equations": [],
        "historical_comparator": [],
        "mappings": [],
        "pdf_residuals": [],
        "query_recoveries": [],
        "source_repairs": [],
    }
    material = {
        "axes": axes,
        "axis_counts": {name: 0 for name in axes},
        "axis_sha256": {
            name: canonical_json_sha256_v1(axis) for name, axis in axes.items()
        },
        "audit_metrics": {
            "mapping_count": 0,
            "pdf_residual_count": 0,
            "query_recovery_count": 0,
            "source_repair_count": 0,
        },
        "base_query_evidence_id": "base-query",
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_comparator_policy_receipt": _policy_receipt(),
        "query_evidence_id": "adapted-query",
        "query_receipt": {},
        "selected_page_json_frontier_sha256": "1" * 64,
        "source_observation_contract": _observation_contract(),
        "spec_refs": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_metrics": {
            "document_count": 0,
            "mapping_count": 0,
            "not_observed_count": 0,
            "ready_count": 0,
            "unresolved_count": 0,
        },
        "sweep_ref": {},
    }
    return {
        **material,
        "audit_id": "geircfav1:audit:" + canonical_json_sha256_v1(material),
    }


def _reseal(audit: dict) -> None:
    material = {key: item for key, item in audit.items() if key != "audit_id"}
    audit["audit_id"] = "geircfav1:audit:" + canonical_json_sha256_v1(material)


def test_pdf_residual_audit_seals_all_71_sources_and_213_balance_pages() -> None:
    value = json.loads(
        (
            ROOT
            / "config/families/"
            "tm-entrusted-investment-risk-capital-pdf-residual-audit-v1.json"
        ).read_bytes()
    )

    checked = runner._validate_pdf_residual_spec_v1(value)

    assert len(checked["residuals"]) == 71
    assert sum(
        len(residual["balance_sheet_page_axis"])
        for residual in checked["residuals"]
    ) == 213
    assert len({item["source_sha256"] for item in checked["residuals"]}) == 71


def test_pdf_residual_provenance_tampering_fails_closed() -> None:
    value = json.loads(
        (
            ROOT
            / "config/families/"
            "tm-entrusted-investment-risk-capital-pdf-residual-audit-v1.json"
        ).read_bytes()
    )
    value["residuals"][0]["balance_sheet_page_axis"][0]["physical_page"] += 1

    with pytest.raises(
        runner.RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error,
        match="identity drifted",
    ):
        runner._validate_pdf_residual_spec_v1(value)


def test_common204_pdf_residual_audit_seals_59_sources_and_177_pages() -> None:
    value = json.loads(
        (
            ROOT
            / "config/families/"
            "tm-entrusted-investment-risk-capital-common204-pdf-residual-audit-v1.json"
        ).read_bytes()
    )

    checked = runner._validate_pdf_residual_spec_v1(value)

    assert len(checked["residuals"]) == 59
    assert sum(
        len(residual["balance_sheet_page_axis"])
        for residual in checked["residuals"]
    ) == 177
    assert checked["residuals"][-1]["document_ordinal"] == 204


def test_disjoint_audit_and_source_observation_contract_are_fail_closed() -> None:
    audit = _audit()
    assert runner.validate_experimental_audit_content_v1(audit)

    overlap = copy.deepcopy(audit)
    overlap["historical_comparator_policy_receipt"]["corpus_relation"][
        "overlap_count"
    ] = 1
    _reseal(overlap)
    with pytest.raises(
        runner.RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error,
        match="semantic gate drifted",
    ):
        runner.validate_experimental_audit_content_v1(overlap)

    invented = copy.deepcopy(audit)
    invented["source_observation_contract"]["status"] = "FAILED"
    invented["source_observation_contract"]["violation_count"] = 1
    _reseal(invented)
    with pytest.raises(
        runner.RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error,
        match="semantic gate drifted",
    ):
        runner.validate_experimental_audit_content_v1(invented)


def test_query_recovery_axis_preserves_source_and_adapter_receipt() -> None:
    indexed = {
        "accepted_clusters": [
            {
                "document_ordinal": 1,
                "entrusted_investment_risk_capital_query_adapter_receipt": {
                    "adapter_query_receipt_id": "receipt"
                },
            }
        ],
        "selected_document_axis": [
            {
                "document_ordinal": 1,
                "source_logical_name": "bank/2025/report.pdf",
                "source_sha256": "2" * 64,
            }
        ],
    }

    assert runner._query_recovery_axis(indexed) == [
        {
            "adapter_query_receipt": {"adapter_query_receipt_id": "receipt"},
            "document_ordinal": 1,
            "source_logical_name": "bank/2025/report.pdf",
            "source_sha256": "2" * 64,
        }
    ]


def test_current_runner_rejects_strict_policy_before_reading_inputs() -> None:
    with pytest.raises(
        runner.RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error,
        match="requires DISJOINT_EXPANSION",
    ):
        runner.run(argparse.Namespace(historical_comparator_policy="STRICT_RELEASE"))


def test_current_corpus_gate_rejects_historical_document() -> None:
    with pytest.raises(
        runner.RunGeminiJsonEntrustedInvestmentRiskCapitalV1Error,
        match="pre-2025",
    ):
        runner._assert_current_corpus(
            {"documents": [{"relative_path": "bank/2024/report.pdf"}]}
        )


def test_source_repairs_outside_a_smaller_current_corpus_are_ignored(tmp_path: Path) -> None:
    repair = {
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "3" * 64,
            "physical_page": 1,
        },
        "repair_id": "geircfav1:repair:" + "4" * 64,
        "repair_kind": "MONEY_CELL_VISIBLE_DASH",
        "source_sha256": "2" * 64,
    }

    assert runner._authenticate_source_repairs_v1(
        repairs=[repair],
        index={"documents": []},
        selected_page_axis=[],
        source_pdf_root=tmp_path,
    ) == []
