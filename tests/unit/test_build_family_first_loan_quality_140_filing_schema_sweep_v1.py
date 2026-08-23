from __future__ import annotations

import copy
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from bctc_ai.evaluation import (
    loan_quality_numeric_row_reconciliation_v1 as reconciliation,
)

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_family_first_loan_quality_140_filing_schema_sweep_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_quality_140_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)

_ROLES = ("STANDARD", "SPECIAL_MENTION", "SUBSTANDARD", "DOUBTFUL", "LOSS")


@dataclass
class _Node:
    canonical_name: str
    display_order: int
    parent_id: int | None
    scope: list[str]
    statement_type: str = "TM"


def _closed_schema() -> dict[str, Any]:
    context = reconciliation.load_loan_quality_margin_context_140_v2(
        _ROOT / sweep_v1.MARGIN_CONTEXT_PATH
    )
    nodes = {
        schema_id: _Node(name, order, parent, ["SEPARATE", "CONSOLIDATED"])
        for order, (schema_id, (name, parent)) in enumerate(
            reconciliation._CORE_SCHEMA.items(), 100
        )
    }
    return reconciliation.project_loan_quality_closed_schema_v1(nodes, context)


def _cell(
    lane: int,
    value: str,
    *,
    line: int,
    page: int = 1,
    viet: str | None = None,
) -> dict[str, Any]:
    return {
        "lane_index": lane,
        "page_sequence": page,
        "ppocrv6_surface": value,
        "source_line_index": line,
        "vietocr_surface": value if viet is None else viet,
    }


def _record(values: tuple[int, int], *, line: int, label: str) -> dict[str, Any]:
    return {
        "cells": [
            _cell(0, str(values[0]), line=line),
            _cell(1, str(values[1]), line=line + 1),
        ],
        "label_surface": label,
    }


def _numeric_evidence(mode: str) -> dict[str, Any]:
    grade_values = ((100, 90), (10, 9), (5, 4), (3, 2), (2, 1))
    rows = []
    for offset, (role, values) in enumerate(zip(_ROLES, grade_values, strict=True)):
        rows.append(
            {
                **_record(values, line=offset * 10, label=role),
                "role": role,
            }
        )
    margin_values = {
        "STANDALONE_AFTER_FIVE_GRADES": (5, 4),
        "INCLUDED_IN_747_VIA_5746": (8, 7),
        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": (8, 7),
    }.get(mode)
    total_values = (125, 110) if mode == "STANDALONE_AFTER_FIVE_GRADES" else (120, 106)
    parent_values = (128, 113) if mode == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE" else None
    source = {
        "format_version": reconciliation.INPUT_FORMAT_VERSION,
        "lane_types": ["MONEY", "MONEY"],
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "margin": (
            None
            if margin_values is None
            else _record(margin_values, line=70, label="Cho vay giao dịch ký quỹ")
        ),
        "margin_mode": mode,
        "parent_total": (
            None
            if parent_values is None
            else _record(parent_values, line=80, label="Cho vay khách hàng")
        ),
        "rows": rows,
        "source_id": f"test:{mode}",
        "sparse_blocks": [],
        "total": _record(total_values, line=60, label="Tổng"),
    }
    return reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)


def _mapping_graph() -> dict[str, Any]:
    return {
        "axes": [
            {"period": "30/06/2026", "x_center_x2": 1000},
            {"period": "31/12/2025", "x_center_x2": 1400},
        ],
        "lane_centers_x2": [1000, 1400],
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "owner_context": {"surface": "Cho vay khách hàng"},
    }


@pytest.mark.parametrize(
    ("mode", "expected_standard", "expected_parent", "expected_count"),
    [
        ("NOT_OBSERVED_DO_NOT_SYNTHESIZE", [100, 90], [120, 106], 5),
        ("STANDALONE_AFTER_FIVE_GRADES", [100, 90], [125, 110], 6),
        ("INCLUDED_IN_747_VIA_5746", [92, 83], [120, 106], 6),
        (
            "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE",
            [100, 90],
            [128, 113],
            6,
        ),
    ],
)
def test_bounded_margin_modes_map_without_double_count_or_backsolve(
    mode: str,
    expected_standard: list[int],
    expected_parent: list[int],
    expected_count: int,
) -> None:
    evidence = _numeric_evidence(mode)
    parent, mappings, checks = sweep_v1._mapping_rows(evidence, _mapping_graph(), _closed_schema())

    assert evidence["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert parent["values"] == expected_parent
    assert len(mappings) == expected_count
    standard = next(item for item in mappings if item["report_norm_id"] == 747)
    assert standard["values"] == expected_standard
    margin = [item for item in mappings if item["report_norm_id"] == 1944]
    assert bool(margin) is (mode != "NOT_OBSERVED_DO_NOT_SYNTHESIZE")
    assert all(
        sum(mapping["values"][lane] for mapping in mappings) == expected_parent[lane]
        for lane in range(2)
    )
    assert all(check["status"] == "EXACT_BOUNDED_MAPPING_TO_OBSERVED_PARENT" for check in checks)
    if mode == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE":
        assert standard["normalization"] == {"operation": "KEEP_OBSERVED_CORE_VALUE_UNCHANGED"}
        assert margin[0]["normalization"]["operation"] == ("EMIT_OBSERVED_1944_KEEP_CORE_UNCHANGED")


def _graph_value(
    lane: int,
    value: int,
    *,
    line: int,
    page: int,
    embedded: bool = False,
) -> dict[str, Any]:
    result = {
        "lane_index": lane,
        "page_sequence": page,
        "source_line_index": line,
        "source_surface": str(value),
        "vietocr_surface": str(value),
    }
    if embedded:
        result.update(
            {
                "embedded_token_ordinal": lane,
                "source_line_surface": f"Không bao gồm ký quỹ {value}",
                "vietocr_line_surface": f"Không bao gồm ký quỹ {value}",
            }
        )
    return result


def _joined_line(line: int, *, page: int, surface: str) -> dict[str, Any]:
    return {
        "bbox": [10, 10 + line, 100, 20 + line],
        "crop_ref": {
            "path": f"test/page-{page}/line-{line}.png",
            "sha256": f"{line + page:064x}"[-64:],
            "size_bytes": 10,
        },
        "line_ordinal": line,
        "numeric_recognition": {"raw_prediction": surface, "reader_score": 1.0},
        "sample_id": f"sample-test-{page}-{line}",
        "vietocr_text": surface,
    }


def test_excluded_graph_adapter_requires_observed_footnote_and_prior_parent() -> None:
    grade_values = ((100, 90), (10, 9), (5, 4), (3, 2), (2, 1))
    rows = []
    page_two_lines = []
    for row_offset, (role, values) in enumerate(zip(_ROLES, grade_values, strict=True)):
        vectors = []
        for lane, value in enumerate(values):
            line = row_offset * 2 + lane
            vectors.append(_graph_value(lane, value, line=line, page=2))
            page_two_lines.append(_joined_line(line, page=2, surface=str(value)))
        rows.append(
            {
                "label": {"surface": role},
                "role": role,
                "values": vectors,
            }
        )
    core = []
    for lane, value in enumerate((120, 106)):
        line = 10 + lane
        core.append(_graph_value(lane, value, line=line, page=2))
        page_two_lines.append(_joined_line(line, page=2, surface=str(value)))
    # Both embedded tokens are bound to one authenticated whole-line crop.
    margin = [
        _graph_value(0, 8, line=12, page=2, embedded=True),
        _graph_value(1, 7, line=12, page=2, embedded=True),
    ]
    page_two_lines.append(_joined_line(12, page=2, surface="Không bao gồm ký quỹ 8 7"))
    parent = []
    page_one_lines = []
    for lane, value in enumerate((128, 113)):
        parent.append(_graph_value(lane, value, line=lane, page=1))
        page_one_lines.append(_joined_line(lane, page=1, surface=str(value)))
    graph = {
        "axes": [
            {"period": "30/06/2026", "x_center_x2": 1000},
            {"period": "31/12/2025", "x_center_x2": 1400},
        ],
        "lane_centers_x2": [1000, 1400],
        "lane_types": ["MONEY", "MONEY"],
        "layout_mode": "HORIZONTAL_TYPED_PERIOD_LANES",
        "nonadditive_rows": [
            {
                "classification": "NONADDITIVE_EXCLUDED_DISCLOSURE",
                "context_disposition": (
                    "EXPLICIT_EXCLUDED_FOOTNOTE_RECONCILES_CORE_TO_CUSTOMER_LOAN_PARENT"
                ),
                "label_surface": "Không bao gồm cho vay giao dịch ký quỹ",
                "parent_role": None,
                "values": margin,
            }
        ],
        "optional_additive_row": None,
        "owner_context": {"page_sequence": 1, "surface": "Cho vay khách hàng"},
        "page_sequence": 2,
        "rows": rows,
        "totals": {"core": core, "customer_loan_parent": parent, "grand": []},
    }
    joined = [
        {"lines": page_one_lines, "page_sequence": 1, "page_width": 1000},
        {"lines": page_two_lines, "page_sequence": 2, "page_width": 1000},
    ]

    source = sweep_v1._graph_to_numeric_input(graph, "graph:test", joined)
    result = reconciliation.build_loan_quality_numeric_row_reconciliation_v1(source)

    assert source["margin_mode"] == "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"
    assert [cell["page_sequence"] for cell in source["parent_total"]["cells"]] == [1, 1]
    assert [cell["source_line_index"] for cell in source["margin"]["cells"]] == [12, 12]
    assert result["status"] == "EXACT_OBSERVED_NUMERIC_RECONCILIATION"
    assert result["accounting_checks"][-1]["term_roles"] == [
        "PRINTED_QUALITY_TOTAL",
        "MARGIN_AND_SECURITIES_ADVANCE",
    ]

    missing = copy.deepcopy(graph)
    missing["totals"]["customer_loan_parent"] = []
    with pytest.raises(
        sweep_v1.LoanQualityTrialUnresolvedV1Error,
        match="no observed numeric value vector",
    ):
        sweep_v1._graph_to_numeric_input(missing, "graph:test", joined)


def test_e0167_challenger_and_both_exact_crop_refs_are_pinned() -> None:
    challenger, _reference = sweep_v1._strict_challenger(_ROOT)
    assert challenger["evaluation_id"] == sweep_v1._EXPECTED_CHALLENGER_EVALUATION_ID
    assert {item["sample_id"] for item in challenger["observations"]} == set(
        sweep_v1._EXPECTED_CHALLENGER_OBSERVATIONS
    )

    forged = copy.deepcopy(challenger)
    forged["observations"][0]["crop_ref"]["sha256"] = "0" * 64
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="observation drifted",
    ):
        sweep_v1._validate_challenger(forged, _ROOT)

    forged = copy.deepcopy(challenger)
    forged["claim_boundary"] += "_FORGED"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="self-identity drifted",
    ):
        sweep_v1._validate_challenger(forged, _ROOT)

    forged = copy.deepcopy(challenger)
    forged["observations"][0]["inference"]["temperature"] = False
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="observation drifted",
    ):
        sweep_v1._validate_challenger(forged, _ROOT)


def test_e0168_two_requests_and_four_exact_footnote_crops_are_pinned() -> None:
    challenger, _reference = sweep_v1._strict_footnote_challenger(_ROOT)
    assert challenger["evaluation_id"] == sweep_v1._EXPECTED_FOOTNOTE_EVALUATION_ID
    assert challenger["decision"]["fresh_request_count"] == 8
    assert {item["sample_id"] for item in challenger["observations"]} == set(
        sweep_v1._EXPECTED_FOOTNOTE_OBSERVATIONS
    )

    forged = copy.deepcopy(challenger)
    forged["observations"][0]["requests"][1]["credential_slot"] = 1
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="stateless request evidence drifted",
    ):
        sweep_v1._validate_footnote_challenger(forged, _ROOT)

    forged = copy.deepcopy(challenger)
    forged["claim_boundary"] += "_FORGED"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="self-identity drifted",
    ):
        sweep_v1._validate_footnote_challenger(forged, _ROOT)

    forged = copy.deepcopy(challenger)
    forged["observations"][0]["requests"][0]["fresh_request_ordinal"] = True
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="stateless request evidence drifted",
    ):
        sweep_v1._validate_footnote_challenger(forged, _ROOT)


def test_e0168_corroborates_without_overwriting_raw_reader_surfaces() -> None:
    evaluation, _reference = sweep_v1._strict_footnote_challenger(_ROOT)
    sample_id = "sample-000038000"
    observation = next(
        item for item in evaluation["observations"] if item["sample_id"] == sample_id
    )
    expected = sweep_v1._EXPECTED_FOOTNOTE_OBSERVATIONS[sample_id]
    raw_vietocr_tokens = ["16.266.352", "8.689,759"]
    values = [
        {
            "embedded_token_ordinal": lane,
            "lane_index": lane,
            "lane_type": "MONEY",
            "page_sequence": 18,
            "role": "NONADDITIVE_EXCLUDED_DISCLOSURE",
            "source_line_index": 26,
            "source_line_surface": None,
            "source_surface": None,
            "vietocr_line_surface": observation["vietocr_transformer_surface"],
            "vietocr_surface": raw_vietocr_tokens[lane],
        }
        for lane in range(2)
    ]
    graph = {
        "lane_types": ["MONEY", "MONEY"],
        "nonadditive_rows": [
            {
                "classification": "NONADDITIVE_EXCLUDED_DISCLOSURE",
                "context_disposition": (
                    "EXPLICIT_EXCLUDED_FOOTNOTE_RECONCILES_CORE_TO_CUSTOMER_LOAN_PARENT"
                ),
                "label_source_line_indices": [26, 27],
                "values": values,
            }
        ],
        "totals": {
            "customer_loan_parent": [
                {"page_sequence": 17, "source_line_index": lane} for lane in range(2)
            ]
        },
    }
    joined = [
        {
            "lines": [
                {
                    "crop_ref": expected["crop_ref"],
                    "line_ordinal": 26,
                    "numeric_recognition": {
                        "raw_prediction": observation["ppocrv6_original_surface"]
                    },
                    "sample_id": sample_id,
                    "vietocr_text": observation["vietocr_transformer_surface"],
                }
            ],
            "page_sequence": 18,
        }
    ]

    bound, hits = sweep_v1._bind_excluded_footnote_challenger(graph, joined, evaluation)
    bound_values = bound["nonadditive_rows"][0]["values"]
    assert [item["vietocr_surface"] for item in bound_values] == raw_vietocr_tokens
    assert [item["source_surface"] for item in bound_values] == [None, None]
    lookup = sweep_v1._source_line_lookup(joined)
    cells = sweep_v1._input_cells(bound_values, lookup, page_hint=18)
    assert [item["vietocr_surface"] for item in cells] == raw_vietocr_tokens
    assert [item["ppocrv6_surface"] for item in cells] == [
        observation["ppocrv6_original_surface"],
        observation["ppocrv6_original_surface"],
    ]
    assert len(hits) == 1


def test_e0167_corroborates_single_parseable_vietocr_without_relabeling_conflict() -> None:
    challenger, _reference = sweep_v1._strict_challenger(_ROOT)
    sample_id = "sample-000384932"
    observation = next(
        item for item in challenger["observations"] if item["sample_id"] == sample_id
    )
    expected = sweep_v1._EXPECTED_CHALLENGER_OBSERVATIONS[sample_id]
    cell = {
        "lane_index": 1,
        "lane_type": "MONEY",
        "page_sequence": 21,
        "ppocrv6_surface": observation["ppocrv6_original_surface"],
        "selected_readers": ["VIETOCR"],
        "selected_value": sweep_v1._integer_surface(expected["selected_surface"]),
        "source_line_index": 31,
        "status": "SELECTED_SINGLE_PARSEABLE_OBSERVATION",
        "vietocr_surface": observation["vietocr_transformer_surface"],
    }
    evidence = {
        "accounting_checks": [
            {
                "required_for_acceptance": True,
                "status": "EXACT_OBSERVED_EQUATION",
            }
        ],
        "rows": [{"cells": [cell]}],
        "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
    }
    joined = [
        {
            "lines": [
                {
                    "crop_ref": expected["crop_ref"],
                    "line_ordinal": 31,
                    "sample_id": sample_id,
                }
            ],
            "page_sequence": 21,
        }
    ]

    hits = sweep_v1._challenger_hits(evidence, joined, challenger)

    assert hits == [
        {
            "crop_ref": expected["crop_ref"],
            "sample_id": sample_id,
            "selected_value": 1_992_589_394,
            "status": ("PIXEL_VIETOCR_GEMMA4_AND_REQUIRED_EXACT_ACCOUNTING_CORROBORATED"),
        }
    ]
    unresolved = copy.deepcopy(evidence)
    unresolved["accounting_checks"][0]["status"] = "UNRESOLVED_MISSING_OBSERVED_VALUE"
    with pytest.raises(
        sweep_v1.LoanQualityTrialUnresolvedV1Error,
        match="no complete required accounting corroboration",
    ):
        sweep_v1._challenger_hits(unresolved, joined, challenger)


def _terminal_trials() -> list[dict[str, Any]]:
    trials = []
    modes = (
        ["STANDALONE_AFTER_FIVE_GRADES"] * 17
        + ["INCLUDED_IN_747_VIA_5746"] * 6
        + ["EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE"] * 4
        + ["NOT_OBSERVED_DO_NOT_SYNTHESIZE"] * 113
    )
    challenger_samples = list(sweep_v1._EXPECTED_CHALLENGER_OBSERVATIONS)
    footnote_samples = list(sweep_v1._EXPECTED_FOOTNOTE_OBSERVATIONS)
    for ordinal in range(140):
        mode = modes[ordinal]
        margin = mode != "NOT_OBSERVED_DO_NOT_SYNTHESIZE"
        children = [{"report_norm_id": schema_id} for schema_id in (747, 748, 749, 750, 751)]
        if margin:
            children.append({"report_norm_id": 1944})
        trials.append(
            {
                "challenger_hits": (
                    [{"sample_id": challenger_samples[ordinal]}] if ordinal < 2 else []
                ),
                "excluded_footnote_challenger_hits": (
                    [{"sample_id": footnote_samples[ordinal - 23]}] if 23 <= ordinal < 27 else []
                ),
                "mapped_children": children,
                "mapped_parent": {"report_norm_id": 746},
                "numeric_evidence": {
                    "lane_types": (
                        ["MONEY", "PERCENT", "MONEY", "PERCENT"]
                        if ordinal < 4
                        else ["MONEY", "MONEY"]
                    ),
                    "layout_mode": (
                        "HORIZONTAL_TYPED_PERIOD_LANES"
                        if ordinal < 122
                        else "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"
                    ),
                    "margin_mode": mode,
                    "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
                },
                "status": "VERIFIED_BY_CODEX",
            }
        )
    return trials


def test_terminal_complete_is_exactly_140_verified_and_700_plus_27() -> None:
    result = sweep_v1._terminal_material(_terminal_trials(), {"fixture": True})
    assert result["state"] == "COMPLETE"
    assert result["metrics"]["verified_trial_count"] == 140
    assert result["metrics"]["mapped_core_grade_record_count"] == 700
    assert result["metrics"]["mapped_margin_record_count"] == 27
    assert result["metrics"]["mapped_record_count"] == 727
    assert result["metrics"]["excluded_footnote_hosted_gemma4_bound_crop_count"] == 4
    assert result["metrics"]["margin_presentation_mode_trial_counts"] == {
        "STANDALONE_AFTER_FIVE_GRADES": 17,
        "INCLUDED_IN_747_VIA_5746": 6,
        "EXPLICITLY_EXCLUDED_FROM_CORE_VIA_FOOTNOTE": 4,
        "NOT_OBSERVED_DO_NOT_SYNTHESIZE": 113,
    }

    unresolved = _terminal_trials()
    unresolved[0]["status"] = "UNRESOLVED_FAIL_CLOSED"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="unresolved trials",
    ):
        sweep_v1._terminal_material(unresolved, {})

    missing_margin = _terminal_trials()
    missing_margin[0]["mapped_children"].pop()
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match=r"700 \+ 27 = 727",
    ):
        sweep_v1._terminal_material(missing_margin, {})


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda trials: trials[0]["numeric_evidence"].update(
                {"margin_mode": "INCLUDED_IN_747_VIA_5746"}
            ),
            "margin presentation distribution",
        ),
        (
            lambda trials: trials[121]["numeric_evidence"].update(
                {"layout_mode": "STACKED_PERIOD_BLOCKS_MULTI_ASSET_COLUMNS"}
            ),
            "layout distribution",
        ),
        (
            lambda trials: trials[4]["numeric_evidence"].update(
                {"lane_types": ["MONEY", "PERCENT", "MONEY", "PERCENT"]}
            ),
            "typed-lane distribution",
        ),
        (
            lambda trials: trials[24]["excluded_footnote_challenger_hits"][0].update(
                {"sample_id": trials[23]["excluded_footnote_challenger_hits"][0]["sample_id"]}
            ),
            "E-0168 excluded-footnote crops",
        ),
    ],
)
def test_terminal_distribution_falsifiers_reject_coordinated_tamper(
    mutator: Any, message: str
) -> None:
    trials = _terminal_trials()
    mutator(trials)
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match=message,
    ):
        sweep_v1._terminal_material(trials, {})


def test_terminal_typed_axis_rejects_bool_instead_of_string() -> None:
    trials = _terminal_trials()
    trials[0]["numeric_evidence"]["lane_types"][0] = True
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="typed lane axis drifted",
    ):
        sweep_v1._terminal_material(trials, {})


def test_public_replay_rejects_coordinated_trial_mutation(monkeypatch, tmp_path) -> None:
    expected = {
        "metrics": {"verified_trial_count": 140, "mapped_record_count": 727},
        "state": "COMPLETE",
        "sweep_id": "lq140v1:sweep:" + "1" * 64,
        "trials": [{"status": "VERIFIED_BY_CODEX"}],
    }
    monkeypatch.setattr(
        sweep_v1,
        "build_authenticated_family_first_loan_quality_140_filing_schema_sweep_v1",
        lambda *_args: copy.deepcopy(expected),
    )
    assert (
        sweep_v1.validate_authenticated_family_first_loan_quality_140_filing_schema_sweep_replay_v1(
            expected, object(), tmp_path
        )
        == expected
    )
    forged = copy.deepcopy(expected)
    forged["trials"][0]["status"] = "UNRESOLVED_FAIL_CLOSED"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="does not replay exactly",
    ):
        sweep_v1.validate_authenticated_family_first_loan_quality_140_filing_schema_sweep_replay_v1(
            forged, object(), tmp_path
        )


def test_output_publication_is_atomic_exclusive_and_cleans_failed_stage(
    monkeypatch, tmp_path
) -> None:
    destination = tmp_path / "result.json"
    payload = b'{"state":"COMPLETE"}\n'

    sweep_v1._write_exclusive(destination, payload)

    assert destination.read_bytes() == payload
    assert [path.name for path in tmp_path.iterdir()] == ["result.json"]
    with pytest.raises(
        sweep_v1.FamilyFirstLoanQuality140FilingSchemaSweepV1Error,
        match="destination already exists",
    ):
        sweep_v1._write_exclusive(destination, payload)

    failed_destination = tmp_path / "failed.json"

    def fail_link(*_args, **_kwargs):
        raise OSError(5, "injected publication failure")

    monkeypatch.setattr(sweep_v1.os, "link", fail_link)
    with pytest.raises(OSError, match="injected publication failure"):
        sweep_v1._write_exclusive(failed_destination, payload)
    assert not failed_destination.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["result.json"]
