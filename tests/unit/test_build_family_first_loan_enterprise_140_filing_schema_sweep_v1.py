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
                "row_proposals": [
                    {
                        "evidence": [{"page_sequence": 5, "source_line_index": 0}],
                        "proposal_id": "evidence-6058",
                        "report_norm_id": 6058,
                        "schema_parent_report_norm_id": 727,
                        "status": "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY",
                    }
                ],
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


def _flat_numeric_inputs(
    layout: list[str],
    *,
    report_norm_id: int = 767,
    first_pp: str = "100",
    first_viet: str | None = None,
) -> dict:
    surfaces = [first_pp, "25.00", "90", "25.00"] if len(layout) == 4 else [first_pp, "90"]
    viet_surfaces = list(surfaces)
    viet_surfaces[0] = first_viet if first_viet is not None else first_pp

    def value(sample_id: str, column: int, surface: str) -> dict:
        return {
            "column_ordinal": column,
            "parsed_token": sweep_v1.parse_visible_financial_numeric_token_v1(surface),
            "raw_prediction": surface,
            "sample_id": sample_id,
        }

    lines = [
        {
            "numeric_recognition": {"raw_prediction": "", "reader_score": 1.0},
            "sample_id": "label",
            "vietocr_text": "Doanh nghiệp nhà nước",
        }
    ]
    row_values = []
    total_values = []
    for column, (pp_surface, viet_surface) in enumerate(zip(surfaces, viet_surfaces, strict=True)):
        sample_id = f"row-{column}"
        row_values.append(value(sample_id, column, pp_surface))
        lines.append(
            {
                "numeric_recognition": {"raw_prediction": pp_surface, "reader_score": 1.0},
                "sample_id": sample_id,
                "vietocr_text": viet_surface,
            }
        )
    for column, surface in enumerate(surfaces):
        sample_id = f"total-{column}"
        total_values.append(value(sample_id, column, surface))
        lines.append(
            {
                "numeric_recognition": {"raw_prediction": surface, "reader_score": 1.0},
                "sample_id": sample_id,
                "vietocr_text": surface,
            }
        )
    parent = 727 if report_norm_id == 6058 else 766
    binding = {
        "binding_id": f"binding-{report_norm_id}",
        "evidence_proposal_id": f"evidence-{report_norm_id}",
        "foreign_branch_or_subsidiary_component": False,
        "report_norm_id": report_norm_id,
        "schema_parent_report_norm_id": parent,
        "status": "UNIQUE_SCHEMA_BINDING_PROPOSAL_NO_MAPPING_AUTHORITY",
    }
    graph_region = {
        "binding_proposals": [binding],
        "row_proposals": [
            {
                "evidence": [{"page_sequence": 5, "source_line_index": 0}],
                "proposal_id": binding["evidence_proposal_id"],
                "report_norm_id": report_norm_id,
                "schema_parent_report_norm_id": parent,
                "status": "SCHEMA_ROW_TEXT_AND_GEOMETRY_PROPOSAL_REQUIRES_REPLAY",
            }
        ],
    }
    closure = {
        "exact_total_candidates": [{"sample_ids": [item["sample_id"] for item in total_values]}],
        "row_axis_id": "afrav1:axis:test",
        "status": "CORROBORATED_EXACT_UNIQUE_TRAILING_TOTAL",
        "unresolved_reasons": [],
    }
    schema_proposal = {
        "evidence_proposal_id": binding["evidence_proposal_id"],
        "graph_binding_id": binding["binding_id"],
        "report_norm_id": report_norm_id,
        "schema_parent_report_norm_id": parent,
        "schema_projection_id": "lebspv1:projection:test",
        "status": "LIVE_SCHEMA_IDENTITY_JOIN_PROPOSAL_ONLY_AWAITS_NUMERIC",
    }
    schema_proposal["proposal_id"] = "lef12s140v1:schema:" + canonical_json_sha256_v1(
        schema_proposal
    )
    return {
        "closure": closure,
        "context": _context(layout),
        "graph_region": graph_region,
        "page_binding": [{"local_page_sequence": 1, "physical_page": 5}],
        "pages": [{"lines": lines, "page_sequence": 1, "page_width": 1000}],
        "row_axis": {
            "metrics": {"missing_lane_count": 0},
            "row_axis_id": "afrav1:axis:test",
            "rows": [
                {
                    "label_match": {
                        "end_source_line_index": 0,
                        "page_sequence": 1,
                        "source_line_index": 0,
                    },
                    "missing_column_ordinals": [],
                    "role": "STATE_ENTERPRISE_LOANS",
                    "role_kind": "ADDITIVE_CHILD",
                    "values": row_values,
                }
            ],
            "trailing_value_rows": [{"values": total_values}],
        },
        "schema_proposals": [schema_proposal],
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


def test_flat_four_lane_numeric_gate_maps_money_and_retains_percent_only_as_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _flat_numeric_inputs(
        ["MONEY", "PERCENT", "MONEY", "PERCENT"],
        first_pp="1.000",
        first_viet="1,000",
    )
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )

    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )

    assert stage["status"] == "EXACT_FLAT_TABLE_NUMERIC_ACCOUNTING_AND_SCHEMA_BOUND"
    assert stage["unresolved_reasons"] == []
    assert len(stage["mapped_rows"]) == 1
    assert [cell["column_ordinal"] for cell in stage["mapped_rows"][0]["money_cells"]] == [
        0,
        2,
    ]
    percent = [cell for cell in stage["numeric_cells"] if cell["unit"]["unit_kind"] == "PERCENT"]
    assert len(percent) == 4
    assert all(cell["emission_eligible"] is False for cell in percent)


@pytest.mark.parametrize(
    ("pp_surface", "viet_surface", "reason_prefix"),
    [
        ("-", "-", "PIXEL_DASH_EVIDENCE_REQUIRED:"),
        ("100", "101", "PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT:"),
        ("+100", "100", "PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT:"),
        ("-0", "0", "PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT:"),
        ("-100", "(100)", "PPOCRV6_VIETOCR_TYPED_TOKEN_CONFLICT:"),
    ],
)
def test_dash_or_cross_reader_conflict_never_uses_additive_closure_to_repair_a_cell(
    monkeypatch: pytest.MonkeyPatch,
    pp_surface: str,
    viet_surface: str,
    reason_prefix: str,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"], first_pp=pp_surface, first_viet=viet_surface)
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )

    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )

    assert stage["status"] == "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES"
    assert stage["mapped_rows"] == []
    assert any(reason.startswith(reason_prefix) for reason in stage["unresolved_reasons"])


@pytest.mark.parametrize("falsifier", ["VISIBLE_GROUP", "AMBIGUOUS_GRAPH_ROW"])
def test_flat_gate_rejects_nested_or_source_only_population(
    monkeypatch: pytest.MonkeyPatch,
    falsifier: str,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"])
    if falsifier == "VISIBLE_GROUP":
        inputs["row_axis"]["rows"][0]["role_kind"] = "STRUCTURAL_GROUP"
    else:
        inputs["graph_region"]["row_proposals"].append(
            {
                "evidence": [{"page_sequence": 5, "source_line_index": 1}],
                "proposal_id": "source-only-ambiguous",
                "report_norm_id": None,
                "schema_parent_report_norm_id": None,
                "status": "DUPLICATE_SCHEMA_ROLE_SOURCE_ONLY_AMBIGUOUS",
            }
        )
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )

    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )

    assert stage["mapped_rows"] == []
    assert "NESTED_OR_SOURCE_ONLY_ROW_REQUIRES_DECLARED_CLOSURE" in stage["unresolved_reasons"]


def test_flat_gate_rejects_an_extra_complete_additive_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"])
    extra = copy.deepcopy(inputs["row_axis"]["rows"][0])
    extra["label_match"]["source_line_index"] = 1
    extra["label_match"]["end_source_line_index"] = 1
    extra["role"] = "OTHER_COMPLETE_ADDITIVE_ROW"
    lines = inputs["pages"][0]["lines"]
    for value in extra["values"]:
        source = next(line for line in lines if line["sample_id"] == value["sample_id"])
        value["sample_id"] = "extra-" + value["sample_id"]
        extra_line = copy.deepcopy(source)
        extra_line["sample_id"] = value["sample_id"]
        lines.append(extra_line)
    inputs["row_axis"]["rows"].append(extra)
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )

    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )

    assert stage["mapped_rows"] == []
    assert "NESTED_OR_SOURCE_ONLY_ROW_REQUIRES_DECLARED_CLOSURE" in stage["unresolved_reasons"]


def test_exact_crosslinks_reject_wrong_closure_axis_and_forged_rnid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"])
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )
    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )
    trial = {
        "column_context": inputs["context"],
        "graph_region": inputs["graph_region"],
        "numeric_stage": stage,
        "row_axis": inputs["row_axis"],
        "schema_binding_proposals": inputs["schema_proposals"],
        "sparse_topology_replays": [{"page_binding": inputs["page_binding"], "scan": {}}],
    }
    assert sweep_v1._valid_exact_trial_crosslinks(trial, "lebspv1:projection:test")

    wrong_axis = copy.deepcopy(trial)
    wrong_axis["numeric_stage"]["accounting_closure"]["row_axis_id"] = "afrav1:axis:wrong"
    assert not sweep_v1._valid_exact_trial_crosslinks(wrong_axis, "lebspv1:projection:test")
    forged_rnid = copy.deepcopy(trial)
    forged_rnid["numeric_stage"]["mapped_rows"][0]["report_norm_id"] = 999999
    assert not sweep_v1._valid_exact_trial_crosslinks(forged_rnid, "lebspv1:projection:test")


def test_numeric_stage_exact_nested_schemas_reject_extra_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"])
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )
    monkeypatch.setattr(sweep_v1.additive_v1, "_validate_result", lambda value: value)
    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )
    assert sweep_v1._valid_numeric_stage(stage)

    for forged in ("numeric_cell", "mapped_row", "mapped_cell"):
        tampered = copy.deepcopy(stage)
        target = {
            "numeric_cell": tampered["numeric_cells"][0],
            "mapped_row": tampered["mapped_rows"][0],
            "mapped_cell": tampered["mapped_rows"][0]["money_cells"][0],
        }[forged]
        target["unexpected"] = True
        assert not sweep_v1._valid_numeric_stage(tampered)


def test_6058_requires_nested_source_group_closure_even_when_flat_total_closes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inputs = _flat_numeric_inputs(["MONEY", "MONEY"], report_norm_id=6058)
    monkeypatch.setattr(
        sweep_v1.additive_v1,
        "build_accounting_additive_table_closure_v1",
        lambda *_args: inputs["closure"],
    )

    stage = sweep_v1._numeric_gate(
        inputs["row_axis"],
        inputs["context"],
        inputs["pages"],
        {},
        inputs["graph_region"],
        inputs["schema_proposals"],
        inputs["page_binding"],
    )

    assert stage["mapped_rows"] == []
    assert (
        "NESTED_SOURCE_GROUP_CLOSURE_REQUIRED_FOR_REPORT_NORM_ID_6058"
        in stage["unresolved_reasons"]
    )


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


def test_6058_structural_exact_stays_unresolved_without_nested_source_group_closure(
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
    unresolved_numeric = {
        "accounting_closure": None,
        "mapped_rows": [],
        "numeric_cells": [],
        "status": "UNRESOLVED_NUMERIC_ACCOUNTING_OR_SCHEMA_GATES",
        "unresolved_reasons": ["NESTED_SOURCE_GROUP_CLOSURE_REQUIRED_FOR_REPORT_NORM_ID_6058"],
    }
    monkeypatch.setattr(sweep_v1, "_numeric_gate", lambda *_args: unresolved_numeric)

    trial = sweep_v1._trial(
        _document(_exact_graph()),
        {"joined_pages": [_page(4), _page(5)]},
        _projection(),
        None,
        {},
        _schema(),
    )

    assert trial["structural_disposition"] == "EXACT"
    assert trial["terminal_disposition"] == "UNRESOLVED"
    assert trial["column_layout"] == layout
    assert trial["numeric_stage"] == unresolved_numeric
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
