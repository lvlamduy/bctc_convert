from __future__ import annotations

import copy

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import run_gemini_json_currency_risk_family_v1 as runner


def _empty_audit() -> dict:
    axis_names = (
        "clusters",
        "equations",
        "historical_documents",
        "historical_equations",
        "historical_mappings",
        "historical_source_only",
        "mappings",
        "nonclosing_frontiers",
        "period_assignments",
        "source_only_columns",
        "table_receipts",
        "unresolved_documents",
        "unit_receipts",
    )
    axes = {name: [] for name in axis_names}
    material = {
        "audit_metrics": runner._audit_metrics(axes),
        "axis_counts": {name: 0 for name in axis_names},
        "axis_sha256": {name: canonical_json_sha256_v1([]) for name in axis_names},
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": [],
        "query_evidence_id": "query",
        "sweep_id": "sweep",
        **axes,
    }
    return {
        "audit_id": "gjfcreav1:audit:" + canonical_json_sha256_v1(material),
        **material,
    }


def _rehash(audit: dict) -> None:
    audit["audit_id"] = "gjfcreav1:audit:" + canonical_json_sha256_v1(
        {key: value for key, value in audit.items() if key != "audit_id"}
    )


def test_historical_oracle_bytes_and_denominator_are_pinned() -> None:
    oracles = runner._historical_oracles()
    assert [len(value["trials"]) for _ref, value in oracles] == [8, 8]
    assert [reference["sha256"] for reference, _value in oracles] == [
        "ec209921d958cd248dfb4c92767a0347931d085e648c67c879fe72f9de9b488b",
        "422c0a86112833ff8205522d6eb302857eb6e256b829a2fcde43cc9eb4697ba6",
    ]


def test_historical_value_axis_normalizes_only_declared_periods() -> None:
    assert runner._historical_value_axis(
        [
            {
                "normalized_value": 7,
                "period_axis": "CURRENT",
                "source_period_date": "2025-12-31",
            }
        ]
    ) == [{"coefficient": 7, "period_date": "2025-12-31", "period_role": "CURRENT_PERIOD"}]
    with pytest.raises(runner.RunGeminiJsonCurrencyRiskFamilyV1Error):
        runner._historical_value_axis(
            [
                {
                    "normalized_value": 7,
                    "period_axis": "FORECAST",
                    "source_period_date": "2025-12-31",
                }
            ]
        )


def test_audit_content_rejects_coherently_rehashed_metric_drift() -> None:
    audit = _empty_audit()
    assert runner.validate_currency_risk_experimental_audit_content_v1(audit) == audit
    forged = copy.deepcopy(audit)
    forged["audit_metrics"]["mapping_count"] = 1
    _rehash(forged)
    with pytest.raises(runner.RunGeminiJsonCurrencyRiskFamilyV1Error, match="metrics drifted"):
        runner.validate_currency_risk_experimental_audit_content_v1(forged)


def test_audit_content_rejects_unsealed_axis_mutation() -> None:
    forged = _empty_audit()
    forged["nonclosing_frontiers"].append({"forged": True})
    _rehash(forged)
    with pytest.raises(runner.RunGeminiJsonCurrencyRiskFamilyV1Error, match="axis seal drifted"):
        runner.validate_currency_risk_experimental_audit_content_v1(forged)


def test_release_pins_lock_complete_140_document_mapping_axis() -> None:
    assert runner.PINNED_RELEASE_METRICS == {
        "document_count": 140,
        "mapping_count": 3632,
        "not_observed_count": 0,
        "ready_count": 140,
        "unresolved_count": 0,
    }
    assert runner.PINNED_AUDIT_METRICS["mapping_value_count"] == 3512
    assert runner.PINNED_AUDIT_METRICS["historical_mapping_match_count"] == 258
    assert runner.PINNED_AUDIT_METRICS["historical_equation_match_count"] == 122
    assert runner.PINNED_AUDIT_METRICS["historical_source_only_match_count"] == 18
