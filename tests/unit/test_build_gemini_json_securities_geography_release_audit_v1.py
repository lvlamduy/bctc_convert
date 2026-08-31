from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest
from test_gemini_json_securities_geography_family_v1 import _fixture

from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/experiments/build_gemini_json_securities_geography_release_audit_v1.py"
SPEC = importlib.util.spec_from_file_location("securities_geography_release_audit_test", PATH)
assert SPEC is not None and SPEC.loader is not None
audit_runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_runner
SPEC.loader.exec_module(audit_runner)


def _historical_oracle() -> dict:
    return {
        "trials": [
            {
                "document_provenance": "TARGET",
                "source_pdf_sha256": "b" * 64,
                "status": "VERIFIED_BY_CODEX",
                "verified_mappings": [
                    {
                        "report_norm_id": 5760,
                        "semantic_role": "DOMESTIC",
                        "values": [{"normalized_value": 100}],
                    },
                    {
                        "report_norm_id": 5761,
                        "semantic_role": "FOREIGN",
                        "values": [{"normalized_value": 0}],
                    },
                ],
            },
            {
                "document_provenance": "ABSENT",
                "source_pdf_sha256": "3" * 64,
                "status": "NOT_OBSERVED_IN_BOUND_REPORT",
            },
        ]
    }


def test_release_audit_rebuilds_query_candidates_axes_and_historical_comparator(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    sweep_path = tmp_path / "sweep.json"
    sweep_path.write_bytes(canonical_json_bytes_v1(fixture["sweep"]))
    query_receipt = audit_runner._query_receipt(
        fixture["database"],
        selected_ids=fixture["selected"],
        compiled=fixture["compiled"],
    )
    spec_refs = {
        name: {"path": f"{name}.json", "sha256": "1" * 64, "size_bytes": 1}
        for name in ("evaluation", "schema_binding", "topology")
    }
    oracle = _historical_oracle()
    oracle_ref = {"path": "oracle.json", "sha256": "2" * 64, "size_bytes": 1}
    audit = audit_runner.build_securities_geography_release_audit_v1(
        sweep=fixture["sweep"],
        sweep_path=sweep_path,
        selected_ids=fixture["selected"],
        query_receipt=query_receipt,
        spec_refs=spec_refs,
        historical_oracle=oracle,
        historical_oracle_ref=oracle_ref,
    )

    assert audit_runner.validate_securities_geography_release_audit_content_v1(audit) == audit
    assert audit["axis_counts"] == {
        "clusters": 1,
        "historical_comparator": 3,
        "mappings": 2,
        "source_table_closures": 1,
        "unmapped_source_blanks": 0,
    }
    assert audit["audit_metrics"]["historical_mismatch_count"] == 0
    assert (
        audit_runner.validate_securities_geography_release_audit_replay_v1(
            audit,
            database=fixture["database"],
            sweep=fixture["sweep"],
            sweep_path=sweep_path,
            selected_ids=fixture["selected"],
            compiled=fixture["compiled"],
            spec_refs=spec_refs,
            historical_oracle=oracle,
            historical_oracle_ref=oracle_ref,
        )
        == audit
    )

    attacked = copy.deepcopy(audit)
    attacked["axes"]["mappings"][0]["report_norm_id"] = 999999
    with pytest.raises(
        audit_runner.BuildGeminiJsonSecuritiesGeographyReleaseAuditV1Error,
        match="axis seal drifted",
    ):
        audit_runner.validate_securities_geography_release_audit_content_v1(attacked)


def test_historical_absence_can_only_be_superseded_by_one_replayed_ready_candidate(
    tmp_path: Path,
) -> None:
    fixture = _fixture(tmp_path)
    oracle = {
        "trials": [
            {
                "document_provenance": "NEW_SOURCE_DISCOVERY",
                "source_pdf_sha256": "b" * 64,
                "status": "NOT_OBSERVED_IN_BOUND_REPORT",
            }
        ]
    }

    axis = audit_runner._historical_comparator_axis(
        sweep=fixture["sweep"], historical_oracle=oracle
    )

    assert axis[0]["disposition"] == (
        "SUPERSEDED_BOUNDED_ABSENCE_BY_AUTHENTICATED_SELECTED_JSON_SOURCE"
    )
