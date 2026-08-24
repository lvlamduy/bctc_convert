from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

_ROOT = Path(__file__).resolve().parents[2]
_PATH = (
    _ROOT / "scripts/experiments/build_family_first_loan_enterprise_140_filing_schema_sweep_v1.py"
)
_SPEC = importlib.util.spec_from_file_location("loan_enterprise_140_structural_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _page(physical_page: int) -> dict:
    return {"lines": [], "page_sequence": physical_page, "page_width": 1000}


def _period(column: int, value: str) -> dict:
    return {
        "column_center": float(100 + column * 100),
        "column_ordinal": column,
        "evidence_locations": [{"page_sequence": 1, "source_line_index": column}],
        "projection_status": "LOCAL_EXACT",
        "resolved_period": value,
    }


def _unit(column: int, kind: str) -> dict:
    return {
        "column_center": float(100 + column * 100),
        "column_ordinal": column,
        "currency": "VND" if kind == "MONEY" else None,
        "evidence_locations": [{"page_sequence": 1, "source_line_index": column + 4}],
        "magnitude_power10": 6 if kind == "MONEY" else None,
        "projection_status": "LOCAL_EXACT",
        "unit_kind": kind,
    }


def _context(layout: list[str]) -> dict:
    count = len(layout)
    periods = ["2025-12-31"] * (count // 2) + ["2024-12-31"] * (count // 2)
    return {
        "column_context_id": "afccv1:context:test",
        "metrics": {
            "column_count": count,
            "period_column_count": count,
            "unit_column_count": count,
        },
        "period_axis": [_period(index, value) for index, value in enumerate(periods)],
        "row_axis_id": "afrav1:axis:test",
        "status": "PERIOD_UNIT_COLUMN_CONTEXT_RESOLVED_PROPOSAL_ONLY",
        "unit_axis": [_unit(index, kind) for index, kind in enumerate(layout)],
    }


def _zero_scan() -> dict:
    return {
        "metrics": {"core_semantic_anchor_hit_count": 0},
        "near_regions": [],
        "regions": [],
        "scan_id": "aftv1:scan:zero",
        "status": "NOT_OBSERVED_NO_SEMANTIC_ANCHOR_PROPOSAL_ONLY",
    }


def _exact_scan() -> dict:
    return {
        "metrics": {"core_semantic_anchor_hit_count": 2},
        "near_regions": [],
        "regions": [
            {
                "cluster_end_page_sequence_inclusive": 2,
                "minimal_unique_anchor": {
                    "combination_size": 2,
                    "pair_before_triple_search": True,
                },
                "page_sequence": 1,
                "parent_resolution": "EXPLICIT_PARENT",
            }
        ],
        "scan_id": "aftv1:scan:exact",
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
    }


def _document(graph: dict) -> dict:
    return {
        "document_id": "document-1",
        "document_ordinal": 1,
        "evidence_binding": {
            "document_packet_id": "packet-1",
            "outcome_id": "outcome-1",
            "query_spec_id": "query-1",
            "receipt_id": "receipt-1",
            "snapshot_id": "snapshot-1",
        },
        "graph": graph,
        "outcome": {"selected_pages": [4, 5]},
        "result_id": "lef12asv1:document:test",
    }


def _absence_graph() -> dict:
    return {
        "bounded_absences": [{}],
        "branchless_rescue_challengers": [],
        "near_regions": [],
        "regions": [],
    }


def _exact_graph() -> dict:
    return {
        "bounded_absences": [],
        "branchless_rescue_challengers": [],
        "near_regions": [],
        "regions": [
            {
                "binding_proposals": [
                    {
                        "binding_id": "binding-6058",
                        "evidence_proposal_id": "evidence-6058",
                        "report_norm_id": 6058,
                        "schema_parent_report_norm_id": 727,
                        "status": "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY",
                    }
                ],
                "branch": {"page_sequence": 5},
            }
        ],
    }


def _schema() -> dict:
    return {
        "mapped_leaves": [{"parent_report_norm_id": 727, "report_norm_id": 6058}],
        "projection_id": "lebspv1:projection:test",
    }


def _projection() -> dict:
    return {
        "source_binding": {
            "document_page_count": 8,
        }
    }


def test_selected_sparse_runs_never_turn_an_unread_gap_into_a_zero_line_page() -> None:
    runs = sweep_v1._selected_runs(
        {"joined_pages": [_page(2), _page(3), _page(5), _page(8), _page(9)]}
    )

    assert [[item["physical_page"] for item in run["page_binding"]] for run in runs] == [
        [2, 3],
        [5],
        [8, 9],
    ]
    assert [[page["page_sequence"] for page in run["joined_pages"]] for run in runs] == [
        [1, 2],
        [1],
        [1, 2],
    ]
    assert all(4 not in [item["physical_page"] for item in run["page_binding"]] for run in runs)


def test_column_gate_tries_two_and_four_lanes_and_accepts_only_one_resolved_layout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []
    four = _context(["MONEY", "PERCENT", "MONEY", "PERCENT"])

    def build(_axis, _pages, _spec, *, expected_lane_unit_kinds, **_kwargs):
        calls.append(tuple(expected_lane_unit_kinds))
        if len(expected_lane_unit_kinds) == 4:
            return copy.deepcopy(four)
        unresolved = _context(["MONEY", "MONEY"])
        unresolved["status"] = "UNRESOLVED_PERIOD_UNIT_COLUMN_CONTEXT"
        return unresolved

    monkeypatch.setattr(sweep_v1.column_v1, "build_accounting_family_column_context_v1", build)
    monkeypatch.setattr(
        sweep_v1.column_v1,
        "validate_accounting_family_column_context_replay_v1",
        lambda value, *_args, **_kwargs: value,
    )

    context, layout = sweep_v1._column_gate({}, [], {})

    assert calls == [
        ("MONEY", "MONEY"),
        ("MONEY", "PERCENT", "MONEY", "PERCENT"),
    ]
    assert context == four
    assert layout == ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    assert sweep_v1._context_is_resolved(four, layout)
    assert sweep_v1._context_is_resolved(_context(["MONEY", "MONEY"]), ["MONEY", "MONEY"])

    scrambled = copy.deepcopy(four)
    scrambled["period_axis"] = [
        _period(0, "2025-12-31"),
        _period(1, "2024-12-31"),
        _period(2, "2025-12-31"),
        _period(3, "2024-12-31"),
    ]
    assert not sweep_v1._context_is_resolved(scrambled, layout)


def test_live_schema_join_keeps_foreign_branch_at_6058_under_parent_727() -> None:
    proposals = sweep_v1._schema_binding_proposals(_exact_graph()["regions"][0], _schema())

    assert [
        (item["report_norm_id"], item["schema_parent_report_norm_id"]) for item in proposals
    ] == [(6058, 727)]
    assert proposals[0]["status"].endswith("AWAITS_NUMERIC")

    drifted = _exact_graph()["regions"][0]
    drifted["binding_proposals"][0]["schema_parent_report_norm_id"] = 766
    with pytest.raises(sweep_v1.FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error):
        sweep_v1._schema_binding_proposals(drifted, _schema())


def test_not_observed_requires_sparse_and_whole_topology_plus_whole_family12_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    whole_graph = _absence_graph()
    whole_projection = {
        "projection_id": "asrsv1:projection:whole",
        "source_binding": {"selected_pages": list(range(1, 9)), "snapshot_id": "whole"},
    }
    monkeypatch.setattr(sweep_v1, "_scan", lambda _pages, _spec: _zero_scan())
    monkeypatch.setattr(
        sweep_v1,
        "_full_material",
        lambda *_args: ([_page(page) for page in range(1, 9)], whole_projection, whole_graph),
    )

    trial = sweep_v1._trial(
        _document(_absence_graph()),
        {"joined_pages": [_page(4), _page(5)]},
        _projection(),
        {"whole": True},
        {},
        _schema(),
    )

    assert trial["structural_disposition"] == "NOT_OBSERVED"
    assert trial["terminal_disposition"] == "NOT_OBSERVED"
    assert trial["whole_graph"] == whole_graph
    assert trial["whole_graph_binding"]["selected_pages"] == list(range(1, 9))
    assert trial["absence_stage"]["authority"] is False

    challenger = _absence_graph()
    challenger["branchless_rescue_challengers"] = [{}]
    monkeypatch.setattr(
        sweep_v1,
        "_full_material",
        lambda *_args: ([_page(page) for page in range(1, 9)], whole_projection, challenger),
    )
    unresolved = sweep_v1._trial(
        _document(_absence_graph()),
        {"joined_pages": [_page(4), _page(5)]},
        _projection(),
        {"whole": True},
        {},
        _schema(),
    )
    assert unresolved["structural_disposition"] == "UNRESOLVED"


def test_exact_is_only_structurally_ready_and_full_snapshot_is_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan = _exact_scan()
    axis = {
        "metrics": {"missing_lane_count": 0},
        "row_axis_id": "afrav1:axis:test",
        "status": "VISIBLE_ROW_LANE_AXIS_BOUND_PROPOSAL_ONLY",
        "topology_scan_id": scan["scan_id"],
    }
    layout = ["MONEY", "PERCENT", "MONEY", "PERCENT"]
    monkeypatch.setattr(sweep_v1, "_scan", lambda _pages, _spec: scan)
    monkeypatch.setattr(sweep_v1.row_v1, "build_accounting_family_row_axis_v1", lambda *_args: axis)
    monkeypatch.setattr(
        sweep_v1.row_v1,
        "validate_accounting_family_row_axis_replay_v1",
        lambda value, *_args: value,
    )
    monkeypatch.setattr(sweep_v1, "_column_gate", lambda *_args: (_context(layout), layout))

    trial = sweep_v1._trial(
        _document(_exact_graph()),
        {"joined_pages": [_page(4), _page(5)]},
        _projection(),
        None,
        {},
        _schema(),
    )

    assert trial["structural_disposition"] == "EXACT"
    assert trial["terminal_disposition"] == "STRUCTURALLY_READY_FOR_NUMERIC"
    assert trial["column_layout"] == layout
    assert trial["numeric_stage"] == sweep_v1._NUMERIC_PLACEHOLDER
    assert trial["whole_graph"] is None
    assert trial["schema_binding_proposals"][0]["report_norm_id"] == 6058

    with pytest.raises(
        sweep_v1.FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error,
        match="whole snapshot is required only",
    ):
        sweep_v1._trial(
            _document(_exact_graph()),
            {"joined_pages": [_page(4), _page(5)]},
            _projection(),
            {"whole": True},
            {},
            _schema(),
        )


def test_graph_batch_denominator_is_exactly_140() -> None:
    material = {
        "authority": copy.deepcopy(sweep_v1.graph_v1._AUTHENTICATED_BATCH_AUTHORITY),
        "claim_boundary": sweep_v1.graph_v1._AUTHENTICATED_BATCH_CLAIM_BOUNDARY,
        "documents": [{} for _ in range(140)],
        "evidence_binding": {
            "manifest_id": "manifest",
            "query_spec_id": "query",
            "receipt_id": "receipt",
        },
        "family_id": sweep_v1.FAMILY_ID,
        "format_version": sweep_v1.graph_v1.AUTHENTICATED_BATCH_FORMAT_VERSION,
        "metrics": {"document_count": 140},
        "state": "FAMILY12_AUTHENTICATED_CORPUS_GRAPH_PROPOSALS_ONLY",
    }
    batch = {
        **material,
        "result_id": "lef12asv1:batch:" + canonical_json_sha256_v1(material),
    }
    assert len(sweep_v1._graph_batch(batch)["documents"]) == 140

    drifted_material = {**material, "documents": material["documents"][:-1]}
    drifted = {
        **drifted_material,
        "result_id": "lef12asv1:batch:" + canonical_json_sha256_v1(drifted_material),
    }
    with pytest.raises(sweep_v1.FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error):
        sweep_v1._graph_batch(drifted)


def test_public_replay_rebuilds_and_rejects_a_rehashed_structural_tamper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rebuilt = {"result_id": "rebuilt", "trials": [{"graph_binding": {"source": "A"}}]}
    tampered = {"result_id": "tampered", "trials": [{"graph_binding": {"source": "B"}}]}
    monkeypatch.setattr(sweep_v1, "_validate_result", copy.deepcopy)
    monkeypatch.setattr(
        sweep_v1,
        "build_family_first_loan_enterprise_140_filing_schema_sweep_v1",
        lambda _structural_input, _project_root: copy.deepcopy(rebuilt),
    )

    assert (
        sweep_v1.validate_family_first_loan_enterprise_140_filing_schema_sweep_replay_v1(
            rebuilt, {}, _ROOT
        )
        == rebuilt
    )
    with pytest.raises(
        sweep_v1.FamilyFirstLoanEnterprise140FilingSchemaSweepV1Error,
        match="does not replay exactly",
    ):
        sweep_v1.validate_family_first_loan_enterprise_140_filing_schema_sweep_replay_v1(
            tampered, {}, _ROOT
        )
