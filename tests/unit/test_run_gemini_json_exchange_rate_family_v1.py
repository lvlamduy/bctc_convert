from __future__ import annotations

import copy

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from scripts.experiments import run_gemini_json_exchange_rate_family_v1 as runner


def _empty_audit() -> dict:
    axis_names = (
        "category_rows",
        "clusters",
        "denominator_receipts",
        "historical_documents",
        "historical_mappings",
        "historical_source_only",
        "mappings",
        "period_assignments",
        "source_only_cells",
        "source_only_rows",
        "unresolved_documents",
    )
    axes = {name: [] for name in axis_names}
    material = {
        "audit_metrics": runner._audit_metrics(axes),
        "axes": axes,
        "axis_counts": {name: 0 for name in axis_names},
        "axis_sha256": {name: canonical_json_sha256_v1([]) for name in axis_names},
        "claim_boundary": "fixture",
        "format_version": runner.AUDIT_FORMAT_VERSION,
        "historical_oracle_refs": [],
        "query_evidence_id": "query",
        "query_receipt": {},
        "state": "EXPERIMENTAL_AUDIT_COMPLETE",
        "sweep_id": "sweep",
    }
    return {
        **material,
        "audit_id": "gjxerav1:audit:" + canonical_json_sha256_v1(material),
    }


def _rehash(audit: dict) -> None:
    audit["audit_id"] = "gjxerav1:audit:" + canonical_json_sha256_v1(
        {key: value for key, value in audit.items() if key != "audit_id"}
    )


def test_historical_oracle_bytes_are_pinned() -> None:
    oracles = runner._historical_oracles()
    assert [len(value["trials"]) for value, _reference in oracles] == [8, 8]
    assert [reference["sha256"] for _value, reference in oracles] == [
        "42d990e585f13a3dab0d9ad983198b89962d3ffb9342ba9e5815b52d015704f0",
        "3d3dd84d2b6b8d1ae48252573271d3ef12bb7b4517e48c07d4783c356478056b",
    ]


def test_audit_content_rejects_coherently_rehashed_metric_drift() -> None:
    audit = _empty_audit()
    assert runner.validate_exchange_rate_experimental_audit_content_v1(audit) == audit
    forged = copy.deepcopy(audit)
    forged["audit_metrics"]["mapping_count"] = 1
    _rehash(forged)
    with pytest.raises(runner.RunGeminiJsonExchangeRateFamilyV1Error, match="metrics drifted"):
        runner.validate_exchange_rate_experimental_audit_content_v1(forged)


def test_audit_content_rejects_unsealed_axis_mutation() -> None:
    forged = _empty_audit()
    forged["axes"]["source_only_rows"].append({"forged": True})
    _rehash(forged)
    with pytest.raises(runner.RunGeminiJsonExchangeRateFamilyV1Error, match="axis seal drifted"):
        runner.validate_exchange_rate_experimental_audit_content_v1(forged)


def test_release_pins_lock_the_complete_category_matrix_axis() -> None:
    assert runner.PINNED_SELECTED_PAGE_JSON_FRONTIER_SHA256 == (
        "601be9fc2a894af2ce4f4c982d5347521a6268a46c075d9cc96f9828baef8ae8"
    )
    if runner.PINNED_RELEASE_METRICS:
        assert runner.PINNED_RELEASE_METRICS == {
            "document_count": 140,
            "mapping_count": 976,
            "not_observed_count": 42,
            "ready_count": 98,
            "unresolved_count": 0,
        }
