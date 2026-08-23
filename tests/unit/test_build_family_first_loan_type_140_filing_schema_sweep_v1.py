from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_MODULE_PATH = (
    _ROOT / "scripts/experiments/build_family_first_loan_type_140_filing_schema_sweep_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("loan_type_140_sweep_v1_test", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _schema() -> dict[int, dict[str, object]]:
    return {
        schema_id: {
            "canonical_name": f"schema-{schema_id}",
            "display_order": schema_id,
            "parent_id": 716 if schema_id == 717 else 717,
            "report_norm_id": schema_id,
            "statement_type": "TM",
        }
        for schema_id in {717, *sweep_v1._ROLE_TO_SCHEMA_ID.values()}
    }


def _row(role: str, current: int, previous: int, surface: str) -> dict[str, object]:
    return {
        "cells": [
            {"parsed_value": current},
            {"parsed_value": previous},
        ],
        "label": {"source_line_indices": [1], "surface": surface},
        "role": role,
    }


def _evidence() -> dict[str, object]:
    return {
        "lane_types": ["MONEY", "MONEY"],
        "rows": [
            _row("DOMESTIC_ORGANIZATIONS_INDIVIDUALS", 100, 90, "Trong nước"),
            _row("OTHER_LOANS", 2, 3, "Cho vay khác"),
            _row("UNMAPPED_OTHER_CREDIT", 4, 5, "Cấp tín dụng khác"),
        ],
        "total": [{"parsed_value": 113}, {"parsed_value": 105}],
        "unmodelled_additive_rows": [_row("UNMODELLED_ADDITIVE_OTHER", 7, 7, "Cho vay thấu chi")],
    }


def _graph() -> dict[str, object]:
    return {
        "lane_centers_x2": [1000, 1400],
        "owner": {"source_line_indices": [1], "surface": "Cho vay khách hàng"},
        "period_axis": [
            {"evidence_source_line_indices": [2], "period": "30/06/2026", "x_center_x2": 1000},
            {"evidence_source_line_indices": [3], "period": "31/12/2025", "x_center_x2": 1400},
        ],
    }


def test_other_source_variants_aggregate_once_into_report_norm_726() -> None:
    parent, mappings = sweep_v1._mapping_rows(_evidence(), _graph(), _schema())

    assert parent["report_norm_id"] == 717
    assert parent["values"] == [113, 105]
    other = next(item for item in mappings if item["report_norm_id"] == 726)
    assert other["values"] == [13, 15]
    assert [item["source_role"] for item in other["source_components"]] == [
        "OTHER_LOANS",
        "UNMAPPED_OTHER_CREDIT",
        "UNMODELLED_ADDITIVE_OTHER",
    ]
    assert all(item["status"] == "VERIFIED_BY_CODEX" for item in mappings)


def test_mapping_rejects_a_child_total_mismatch() -> None:
    evidence = _evidence()
    evidence["total"][0]["parsed_value"] = 114
    with pytest.raises(
        sweep_v1.FamilyFirstLoanType140FilingSchemaSweepV1Error,
        match="do not close",
    ):
        sweep_v1._mapping_rows(evidence, _graph(), _schema())


def test_live_schema_projection_requires_every_role_under_parent_717() -> None:
    nodes = {
        schema_id: SimpleNamespace(
            canonical_name=f"schema-{schema_id}",
            display_order=schema_id,
            parent_id=716 if schema_id == 717 else 717,
            statement_type="TM",
        )
        for schema_id in {717, *sweep_v1._ROLE_TO_SCHEMA_ID.values()}
    }
    projected = sweep_v1._schema_projection(nodes)
    assert projected[6057]["parent_id"] == 717
    nodes[726].parent_id = 999
    with pytest.raises(sweep_v1.FamilyFirstLoanType140FilingSchemaSweepV1Error):
        sweep_v1._schema_projection(nodes)


def test_public_replay_rejects_coordinated_trial_mutation(monkeypatch, tmp_path) -> None:
    expected = {
        "authority": {},
        "claim_boundary": "bounded",
        "format_version": "test",
        "inputs": {},
        "metrics": {"verified_trial_count": 140},
        "state": "COMPLETE",
        "sweep_id": "lt140v1:sweep:" + "1" * 64,
        "trials": [{"status": "VERIFIED_BY_CODEX"}],
    }
    monkeypatch.setattr(
        sweep_v1,
        "build_authenticated_family_first_loan_type_140_filing_schema_sweep_v1",
        lambda *_args: copy.deepcopy(expected),
    )
    assert (
        sweep_v1.validate_authenticated_family_first_loan_type_140_filing_schema_sweep_replay_v1(
            expected, object(), tmp_path
        )
        == expected
    )
    tampered = copy.deepcopy(expected)
    tampered["trials"][0]["status"] = "UNRESOLVED"
    with pytest.raises(sweep_v1.FamilyFirstLoanType140FilingSchemaSweepV1Error):
        sweep_v1.validate_authenticated_family_first_loan_type_140_filing_schema_sweep_replay_v1(
            tampered, object(), tmp_path
        )
