from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PATH = _ROOT / "scripts/experiments/build_family_first_loan_maturity_140_filing_schema_sweep_v1.py"
_SPEC = importlib.util.spec_from_file_location("loan_maturity_140_sweep_test", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
sweep_v1 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = sweep_v1
_SPEC.loader.exec_module(sweep_v1)


def _scan(page: int = 5) -> dict[str, Any]:
    return {
        "metrics": {"complete_region_count": 1},
        "regions": [
            {
                "child_matches": [
                    {"page_sequence": page, "role": role}
                    for role in ("SHORT_TERM", "MEDIUM_TERM", "LONG_TERM")
                ],
                "cluster_end_page_sequence_inclusive": page,
                "minimal_unique_anchor": {
                    "combination_size": 2,
                    "pair_before_triple_search": True,
                },
                "page_sequence": page,
                "parent_match": {"page_sequence": page},
            }
        ],
        "status": "ACCEPTED_UNIQUE_TOPOLOGY_PROPOSAL",
        "uniqueness": {"full_match_count": 1},
    }


def test_candidate_page_shortlist_keeps_target_and_immediate_owner_predecessor() -> None:
    packet = {"page_count": 10}
    assert sweep_v1._candidate_pages(_scan(), packet) == (4, 5)

    forged = _scan()
    forged["regions"][0]["minimal_unique_anchor"]["combination_size"] = 3
    with pytest.raises(
        sweep_v1.LoanMaturityTrialUnresolvedV1Error,
        match="pair-first",
    ):
        sweep_v1._candidate_pages(forged, packet)


def test_expanded_matcher_axis_has_only_shortlisted_page_evidence() -> None:
    selected = [
        {
            "lines": [
                {
                    "bbox": [1, 2, 10, 20],
                    "crop_ref": {"path": "crop.png", "sha256": "a" * 64, "size_bytes": 1},
                    "line_ordinal": 0,
                    "numeric_recognition": {"raw_prediction": "123", "reader_score": 0.9},
                    "sample_id": "sample-1",
                    "vietocr_text": "123",
                }
            ],
            "page_sequence": 3,
            "page_width": 100,
        }
    ]

    pages = sweep_v1._expanded_matcher_pages(selected, page_count=5)

    assert [page["page_sequence"] for page in pages] == [1, 2, 3, 4, 5]
    assert [len(page["lines"]) for page in pages] == [0, 0, 1, 0, 0]
    assert pages[2]["lines"][0]["source_text"] == "123"


def test_source_cell_preserves_both_raw_readers_and_rejects_geometry_tamper() -> None:
    raw = {
        "bbox": [10, 20, 30, 40],
        "lane_index": 0,
        "lane_type": "MONEY",
        "semantic_surface": "1.234",
        "source_authoritative": True,
        "source_line_index": 7,
        "surface": "1,234",
    }
    line = {
        "bbox": [10, 20, 30, 40],
        "crop_ref": {"path": "crop.png", "sha256": "b" * 64, "size_bytes": 1},
        "line_ordinal": 7,
        "numeric_recognition": {"raw_prediction": "1,234", "reader_score": 0.8},
        "sample_id": "sample-7",
        "vietocr_text": "1.234",
    }

    cell = sweep_v1._source_cell(raw, role="SHORT_TERM", page_sequence=3, lookup={(3, 7): line})

    assert cell["ppocrv6_surface"] == "1,234"
    assert cell["vietocr_surface"] == "1.234"
    assert cell["crop_sha256"] == "b" * 64

    forged = copy.deepcopy(raw)
    forged["bbox"][2] += 1
    with pytest.raises(
        sweep_v1.LoanMaturityTrialUnresolvedV1Error,
        match="differs from selected authenticated line",
    ):
        sweep_v1._source_cell(forged, role="SHORT_TERM", page_sequence=3, lookup={(3, 7): line})


def test_source_row_preserves_observed_core_label_instead_of_synthetic_role() -> None:
    label_line = {
        "bbox": [10, 20, 90, 40],
        "line_ordinal": 3,
        "numeric_recognition": {"raw_prediction": "No ngan han", "reader_score": 0.9},
        "sample_id": "sample-label",
        "vietocr_text": "Nợ ngắn hạn",
    }
    lookup = {(4, 3): label_line}
    values = []
    for lane, (line_index, surface) in enumerate(((7, "1.234"), (8, "1.111"))):
        line = {
            "bbox": [100 + lane * 50, 20, 140 + lane * 50, 40],
            "crop_ref": {
                "path": f"crop-{lane}.png",
                "sha256": ("a" if lane == 0 else "b") * 64,
                "size_bytes": 1,
            },
            "line_ordinal": line_index,
            "numeric_recognition": {"raw_prediction": surface, "reader_score": 0.9},
            "sample_id": f"sample-{lane}",
            "vietocr_text": surface,
        }
        lookup[(4, line_index)] = line
        values.append(
            {
                "bbox": line["bbox"],
                "lane_index": lane,
                "lane_type": "MONEY",
                "semantic_surface": surface,
                "source_line_index": line_index,
                "surface": surface,
            }
        )
    row = sweep_v1._source_row(
        {
            "label": {
                "bbox": label_line["bbox"],
                "page_sequence": 4,
                "source_line_indices": [3],
                "surface": "Nợ ngắn hạn",
            },
            "values": values,
        },
        role="SHORT_TERM",
        page_sequence=4,
        lookup=lookup,
        lane_types=["MONEY", "MONEY"],
    )

    assert row["label_surface"] == "Nợ ngắn hạn"

    forged = copy.deepcopy(row)
    forged["label_surface"] = "SHORT_TERM"
    assert row != forged


def test_resolved_total_variant_allows_only_exact_challenger_upgrade() -> None:
    evidence = {
        "additional_population": None,
        "core_subtotal": {},
        "grand_total": {},
        "margin": {},
        "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
    }
    graph = {
        "accounting": {"variant": "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"},
        "unresolved_reasons": ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"],
    }
    overlay = {
        "status": "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE",
    }

    assert (
        sweep_v1._resolved_total_variant(evidence, graph, overlay)
        == "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
    )

    with pytest.raises(
        sweep_v1.FamilyFirstLoanMaturity140FilingSchemaSweepV1Error,
        match="differs from its structural graph",
    ):
        sweep_v1._resolved_total_variant(evidence, graph, None)


def _checks(variant: str, four_lane: bool) -> list[dict[str, Any]]:
    checks = []
    for lane in (0, 2) if four_lane else (0, 1):
        names = {
            "CORE_TOTAL_ONLY": [f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}"],
            "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL": [
                f"CORE_BUCKETS_PLUS_MARGIN_EQUAL_GRAND_TOTAL_LANE_{lane}"
            ],
            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL": [
                f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}",
                f"CORE_SUBTOTAL_PLUS_MARGIN_EQUAL_GRAND_TOTAL_LANE_{lane}",
            ],
            "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL": [
                f"CORE_BUCKETS_EQUAL_CORE_SUBTOTAL_LANE_{lane}",
                f"ADDITIONAL_BREAKDOWN_EQUAL_PARENT_LANE_{lane}",
                f"CORE_SUBTOTAL_PLUS_ADDITIONAL_EQUAL_GRAND_TOTAL_LANE_{lane}",
            ],
        }[variant]
        checks.extend(
            {
                "equation_id": name,
                "lane_type": "MONEY",
                "status": "CORROBORATED_EXACT_OBSERVED_EQUATION",
            }
            for name in names
        )
    if four_lane:
        checks.extend(
            {
                "equation_id": f"CORE_PERCENTAGES_EQUAL_PRINTED_PERCENT_TOTAL_LANE_{lane}",
                "lane_type": "PERCENT",
                "status": "CORROBORATED_EXACT_OBSERVED_EQUATION",
            }
            for lane in (1, 3)
        )
    return checks


def _mapping(identifier: int) -> dict[str, Any]:
    return {
        "report_norm_id": identifier,
        "value_cells": [{"selected_value": 1}, {"selected_value": 1}],
    }


def _terminal_trials() -> list[dict[str, Any]]:
    banks = [
        *("ACB" for _ in range(18)),
        *("MBB" for _ in range(18)),
        *("VPB" for _ in range(18)),
        *("HDB" for _ in range(16)),
        *("VCB" for _ in range(18)),
        *("CTG" for _ in range(18)),
        *("BID" for _ in range(16)),
        *("VIB" for _ in range(18)),
    ]
    margin_ordinals = set(range(19, 28)) | set(range(37, 46))
    direct_margin = set(sorted(margin_ordinals)[:12])
    subtotal_margin = margin_ordinals - direct_margin
    additional_ordinals = set(range(55, 61))
    layouts = ["MONEY,PERCENT,MONEY,PERCENT"] * 18 + ["MONEY,MONEY"] * 122
    owners = (
        ["SAME_PAGE_NEAREST_PRECEDING"] * 97
        + ["IMMEDIATE_PRECEDING_PAGE"] * 37
        + ["POST_BRANCH_TABLE_PARENT"] * 6
    )
    periods = (
        ["LOCAL_EXACT_DATES"] * 100
        + ["LOCAL_SPLIT_DATES"] * 22
        + ["LOCAL_RELATIVE_PERIOD_ROLES"] * 12
        + ["LOCAL_RELATIVE_YEAR_END_ROLES"] * 4
        + ["LOCAL_UNAMBIGUOUS_MONTH_DAY_YEAR"]
        + ["BOUND_SOURCE_EXACT_DATE_CHALLENGER"]
    )
    branches = (
        [("TIME_WORDING", "EXPLICIT_PARENT")] * 54
        + [("ORIGINAL_TERM_WORDING", "EXPLICIT_PARENT")] * 44
        + [("INITIAL_TERM_WORDING", "EXPLICIT_PARENT")] * 11
        + [("TERM_WORDING", "EXPLICIT_PARENT")] * 12
        + [("TENOR_WORDING", "EXPLICIT_PARENT")] * 10
        + [("ORIGINAL_TERM_WORDING", "IMPLIED_BY_REQUIRED_CHILD_CLUSTER")] * 6
        + [("INITIAL_TERM_WORDING", "IMPLIED_BY_REQUIRED_CHILD_CLUSTER")]
        + [("TERM_WORDING", "IMPLIED_BY_REQUIRED_CHILD_CLUSTER")] * 2
    )
    units = ["LOCAL_PER_LANE"] * 128 + ["INHERITED_DOCUMENT_MONEY_UNIT"] * 12
    trials = []
    for ordinal, bank in enumerate(banks, 1):
        four_lane = layouts[ordinal - 1] != "MONEY,MONEY"
        if ordinal in direct_margin:
            variant = "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL"
        elif ordinal in subtotal_margin:
            variant = "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL"
        elif ordinal in additional_ordinals:
            variant = "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL"
        else:
            variant = "CORE_TOTAL_ONLY"
        margin = ordinal in margin_ordinals
        dash_count = 2 if ordinal in set(sorted(additional_ordinals)[:4]) else 0
        additional = None
        if ordinal in additional_ordinals:
            additional = {
                "parent": {"cells": [{}, {}]},
                "breakdown_rows": [{"cells": [{}, {}]}],
            }
        mappings = [_mapping(753), _mapping(754), _mapping(755)]
        if margin:
            mappings.append(_mapping(5747))
        conflict = None
        if ordinal == 40:
            conflict = {
                "accounting_checks": [{"status": "CORROBORATED_EXACT"} for _ in range(4)],
                "challenge_evaluation_id": "evaluation-test",
                "result_id": "conflict-test",
                "source_totals": [
                    {
                        "lane_index": lane,
                        "role": role,
                        "sample_id": (
                            sweep_v1._EXPECTED_CONTROL_SAMPLE
                            if (role, lane) == ("CORE_TOTAL", 0)
                            else f"control-{role}-{lane}"
                        ),
                    }
                    for role in ("CORE_TOTAL", "GRAND_TOTAL")
                    for lane in (0, 1)
                ],
                "status": "NUMERIC_EXACT_WITH_TWO_HOSTED_GEMMA4_CONSENSUS_RESCUE",
                "target_resolution": {"sample_id": sweep_v1._EXPECTED_CHALLENGER_SAMPLE},
            }
        raw_variant = "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL" if conflict is not None else variant
        trials.append(
            {
                "challenger_conflict_evidence": conflict,
                "document": {"bank_provenance": bank, "document_id": f"document-{ordinal}"},
                "graph_result": {
                    "graphs": [
                        {
                            "accounting": {"variant": raw_variant},
                            "branch": {
                                "resolution": branches[ordinal - 1][1],
                                "variant": branches[ordinal - 1][0],
                            },
                            "continuation_page_count": 0,
                            "owner": {"mode": owners[ordinal - 1]},
                            "period_axis": {"mode": periods[ordinal - 1]},
                            "unit_scope": {"mode": units[ordinal - 1]},
                            "unresolved_reasons": (
                                ["CORE_PLUS_MARGIN_GRAND_TOTAL_NOT_CORROBORATED"]
                                if conflict is not None
                                else []
                            ),
                        }
                    ],
                    "result_id": f"graph-{ordinal}",
                    "status": "UNRESOLVED" if conflict is not None else "ACCEPTED_VARIANT_GRAPH",
                    "uniqueness": {"minimal_role_combination_proved": True},
                },
                "mapped_children": mappings,
                "numeric_evidence": {
                    "accounting_checks": _checks(variant, four_lane),
                    "additional_population": additional,
                    "core_subtotal": (
                        {}
                        if variant
                        in {
                            "CORE_TOTAL_ONLY",
                            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL",
                            "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL",
                        }
                        else None
                    ),
                    "grand_total": (
                        {}
                        if variant
                        in {
                            "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL",
                            "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL",
                            "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL",
                        }
                        else None
                    ),
                    "lane_types": layouts[ordinal - 1].split(","),
                    "margin": {} if margin else None,
                    "metrics": {
                        "computed_unprinted_core_identity_count": (
                            2 if variant == "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL" else 0
                        ),
                        "percentage_child_cell_count": 6 if four_lane else 0,
                        "percentage_total_control_cell_count": 2 if four_lane else 0,
                        "source_additional_population_count": int(additional is not None),
                        "visible_dash_zero_cell_count": dash_count,
                    },
                    "source_id": f"graph-{ordinal}",
                    "status": "EXACT_OBSERVED_NUMERIC_RECONCILIATION",
                },
                "resolved_total_variant": variant,
                "selected_pages": [1],
                "status": "VERIFIED_BY_CODEX",
            }
        )
    return trials


def test_terminal_gates_pin_all_140_distributions_and_reject_parent_mapping() -> None:
    trials = _terminal_trials()
    inputs = {"hosted_gemma4_challenger_evaluation_id": "evaluation-test", "test": True}
    result = sweep_v1._terminal_material(trials, inputs)

    assert result["metrics"]["mapped_record_count"] == 438
    assert result["metrics"]["observed_accounting_equation_count"] == 352
    assert result["metrics"]["visible_dash_zero_cell_count"] == 8
    assert result["metrics"]["mapped_parent_716_or_752_record_count"] == 0
    assert sum(result["metrics"]["owner_mode_trial_counts"].values()) == 140
    assert result["metrics"]["raw_resolved_total_variant_divergence_count"] == 1
    assert result["metrics"]["raw_total_variant_trial_counts"] == {
        "CORE_TOTAL_ONLY": 116,
        "MARGIN_GRAND_TOTAL_NO_CORE_SUBTOTAL": 13,
        "CORE_SUBTOTAL_MARGIN_GRAND_TOTAL": 5,
        "LEADING_CORE_ADDITIONAL_POPULATION_GRAND_TOTAL": 6,
    }
    assert result["metrics"]["explicit_parent_branch_variant_trial_counts"] == {
        "TIME_WORDING": 54,
        "ORIGINAL_TERM_WORDING": 44,
        "INITIAL_TERM_WORDING": 11,
        "TERM_WORDING": 12,
        "TENOR_WORDING": 10,
    }
    assert result["metrics"]["implied_parent_branch_variant_trial_counts"] == {
        "ORIGINAL_TERM_WORDING": 6,
        "INITIAL_TERM_WORDING": 1,
        "TERM_WORDING": 2,
    }

    forged = copy.deepcopy(trials)
    forged[0]["mapped_children"][0]["report_norm_id"] = 752
    with pytest.raises(
        sweep_v1.FamilyFirstLoanMaturity140FilingSchemaSweepV1Error,
        match="bounded mapping",
    ):
        sweep_v1._terminal_material(forged, inputs)


def test_identical_implied_original_term_surfaces_never_route_by_document() -> None:
    surfaces = ["3.2 Phân tích dư nợ theo thời gian cho vay gốc"] * 6

    assert [sweep_v1.graph_v2._branch_variant(surface) for surface in surfaces] == [
        "ORIGINAL_TERM_WORDING"
    ] * 6


def test_atomic_writer_is_exclusive(tmp_path: Path) -> None:
    target = tmp_path / "result.json"
    sweep_v1._write_exclusive(target, b"{}\n")
    assert target.read_bytes() == b"{}\n"
    with pytest.raises(
        sweep_v1.FamilyFirstLoanMaturity140FilingSchemaSweepV1Error,
        match="destination already exists",
    ):
        sweep_v1._write_exclusive(target, b"forged\n")


def test_formal_implementation_refs_reject_mid_build_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    implementation = tmp_path / "implementation.py"
    implementation.write_text("before\n", encoding="utf-8")
    monkeypatch.setattr(sweep_v1, "_IMPLEMENTATION_PATHS", (Path("implementation.py"),))
    refs = sweep_v1._implementation_refs(tmp_path)

    implementation.write_text("after\n", encoding="utf-8")

    with pytest.raises(
        sweep_v1.FamilyFirstLoanMaturity140FilingSchemaSweepV1Error,
        match="changed during formal build",
    ):
        sweep_v1._assert_implementation_refs_unchanged(tmp_path, refs)
