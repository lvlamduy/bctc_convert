from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_family_first_loan_industry_140_filing_schema_sweep_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_industry_140_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _schema() -> dict[int, dict[str, object]]:
    return {
        schema_id: {
            "canonical_name": f"schema-{schema_id}",
            "display_order": schema_id,
            "parent_id": 716 if schema_id == 727 else 727,
            "report_norm_id": schema_id,
            "statement_type": "TM",
        }
        for schema_id in {727, *sweep_v1._ROLE_TO_SCHEMA_ID.values()}
    }


def _cell(value: int, lane: int) -> dict[str, object]:
    return {"lane_index": lane, "lane_type": "MONEY", "parsed_value": value}


def _evidence(*, rounded: bool = False) -> dict[str, object]:
    return {
        "accounting_checks": [
            {
                "lane_index": 0,
                "residual": -1 if rounded else 0,
                "status": (
                    "CORROBORATED_ROUNDED_SOURCE_EQUATION"
                    if rounded
                    else "EXACT_PP_NUMERIC_EQUATION"
                ),
            },
            {"lane_index": 1, "residual": 0, "status": "EXACT_PP_NUMERIC_EQUATION"},
        ],
        "lane_types": ["MONEY", "MONEY"],
        "rows": [
            {
                "cells": [_cell(10, 0), _cell(9, 1)],
                "label": {"surface": "Vận tải kho bãi"},
                "role": "TRANSPORT_STORAGE",
            },
            {
                "cells": [_cell(2, 0), _cell(1, 1)],
                "label": {"surface": "Hoạt động quản lý Nhà nước"},
                "role": "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY",
            },
            {
                "cells": [_cell(3, 0), _cell(2, 1)],
                "label": {"surface": "Khác"},
                "role": "OTHER_INDUSTRIES",
            },
        ],
        "total": [_cell(16 if rounded else 15, 0), _cell(12, 1)],
        "unmodelled_additive_rows": [],
    }


def _graph() -> dict[str, object]:
    return {
        "customer_loan_context": {"surface": "Cho vay khách hàng"},
        "lane_centers_x2": [1000, 1400],
        "period_axis": [
            {"period": "30/06/2026", "x_center_x2": 1000},
            {"period": "31/12/2025", "x_center_x2": 1400},
        ],
    }


def test_approved_general_variants_map_and_other_roles_aggregate() -> None:
    parent, mappings, checks = sweep_v1._mapping_rows(_evidence(), _graph(), _schema())
    assert parent["report_norm_id"] == 727
    assert parent["values"] == [15, 12]
    assert next(item for item in mappings if item["report_norm_id"] == 736)["values"] == [10, 9]
    other = next(item for item in mappings if item["report_norm_id"] == 745)
    assert other["values"] == [5, 3]
    assert [item["source_role"] for item in other["source_components"]] == [
        "PUBLIC_ADMIN_DEFENCE_SOCIAL_SECURITY",
        "OTHER_INDUSTRIES",
    ]
    assert all(item["status"] == "EXACT_VISIBLE_CHILDREN_TO_PARENT_TOTAL" for item in checks)


def test_source_rounding_is_preserved_not_silently_rewritten() -> None:
    parent, mappings, checks = sweep_v1._mapping_rows(_evidence(rounded=True), _graph(), _schema())
    assert parent["values"][0] == 16
    assert sum(item["values"][0] for item in mappings) == 15
    assert checks[0] == {
        "mapped_child_sum": 15,
        "money_lane_index": 0,
        "printed_parent_total": 16,
        "residual": -1,
        "status": "CORROBORATED_PRINTED_SOURCE_ROUNDING_WITH_EXACT_PERCENT_COMPANION",
    }


def test_unrecognised_accepted_source_role_fails_closed() -> None:
    evidence = _evidence()
    evidence["rows"][0]["role"] = "UNMODELLED_ADDITIVE_OTHER"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanIndustry140FilingSchemaSweepV1Error,
        match="no schema disposition",
    ):
        sweep_v1._mapping_rows(evidence, _graph(), _schema())


def test_live_schema_projection_requires_every_role_under_parent_727() -> None:
    nodes = {
        schema_id: SimpleNamespace(
            canonical_name=f"schema-{schema_id}",
            display_order=schema_id,
            parent_id=716 if schema_id == 727 else 727,
            statement_type="TM",
        )
        for schema_id in {727, *sweep_v1._ROLE_TO_SCHEMA_ID.values()}
    }
    assert sweep_v1._schema_projection(nodes)[6073]["parent_id"] == 727
    nodes[736].parent_id = 999
    with pytest.raises(sweep_v1.FamilyFirstLoanIndustry140FilingSchemaSweepV1Error):
        sweep_v1._schema_projection(nodes)


def test_public_replay_rejects_coordinated_trial_mutation(monkeypatch, tmp_path) -> None:
    expected = {
        "metrics": {"verified_present_trial_count": 98},
        "sweep_id": "li140v1:sweep:" + "1" * 64,
        "trials": [{"status": "VERIFIED_BY_CODEX"}],
    }
    monkeypatch.setattr(
        sweep_v1,
        "build_authenticated_family_first_loan_industry_140_filing_schema_sweep_v1",
        lambda *_args: copy.deepcopy(expected),
    )
    assert (
        sweep_v1.validate_authenticated_family_first_loan_industry_140_filing_schema_sweep_replay_v1(
            expected, object(), tmp_path
        )
        == expected
    )
    forged = copy.deepcopy(expected)
    forged["trials"][0]["status"] = "UNRESOLVED"
    with pytest.raises(sweep_v1.FamilyFirstLoanIndustry140FilingSchemaSweepV1Error):
        sweep_v1.validate_authenticated_family_first_loan_industry_140_filing_schema_sweep_replay_v1(
            forged, object(), tmp_path
        )
