from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

import bctc_ai.mapping.e0038_exact_search as exact_search
from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.e0038_exact_search import (
    E0037_MAX_MONOTONE_SIGNATURE_BOUND,
    E0038_EXACT_SEARCH_HARD_CAP,
    E0038_MAX_TOTAL_SIGNATURE_WORK,
    E0038ExactSearchError,
    E0038ExactSearchStatus,
    plan_e0038_exact_search,
    run_e0038_exact_search,
    validate_e0038_policy_parity,
)
from bctc_ai.mapping.ordered_subgraph_v2 import (
    OrderedSubgraphV2Policy,
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
    SourceStructureRowV2,
    align_ordered_subgraph_v2,
    build_schema_projection_v2,
    load_ordered_subgraph_v2_policy,
    load_ordered_subgraph_v2_policy_bytes,
)
from bctc_ai.schema.registry import SchemaItem


def _policies(project_root: Path):
    baseline = load_ordered_subgraph_v2_policy(
        project_root / "config/mapping/ordered-subgraph-v2.yaml"
    )
    exact = load_ordered_subgraph_v2_policy(
        project_root / "config/mapping/ordered-subgraph-v2-exact-e0038.yaml"
    )
    return baseline, exact


def _projection(node_count: int) -> SchemaProjectionV2:
    items = [
        SchemaItem(
            schema_id=1000 + index,
            canonical_name=f"shared component {index}",
            normalized_name=retrieval_key(f"shared component {index}"),
            statement_type="CDKT",
            display_order=index,
            parent_id=None,
            hierarchy_level=1,
            structural_aliases=[],
            historical_aliases=[],
            scope=["SEPARATE", "CONSOLIDATED"],
        )
        for index in range(node_count)
    ]
    return build_schema_projection_v2(items, "CDKT")


def _named_projection(label: str, *, aliases: tuple[str, ...] = ()) -> SchemaProjectionV2:
    item = SchemaItem(
        schema_id=1000,
        canonical_name=label,
        normalized_name=retrieval_key(label),
        statement_type="CDKT",
        display_order=0,
        parent_id=None,
        hierarchy_level=1,
        structural_aliases=list(aliases),
        historical_aliases=[],
        scope=["SEPARATE", "CONSOLIDATED"],
    )
    return build_schema_projection_v2([item], "CDKT")


def _forty_to_forty_two_case() -> tuple[
    list[SourceStructureRowV2],
    SchemaProjectionV2,
    SchemaProjectionV2,
    list[dict[str, object]],
]:
    anchor_count = 39
    total_count = 41
    rows: list[SourceStructureRowV2] = []
    base_items: list[SchemaItem] = []
    exact_items: list[SchemaItem] = []
    for index in range(total_count):
        canonical = hashlib.sha256(f"canonical-{index}".encode()).hexdigest()
        alias = hashlib.sha256(f"alias-{index}".encode()).hexdigest()
        label = canonical if index < anchor_count else alias
        rows.append(
            SourceStructureRowV2(
                row_id=f"row-{index}",
                order=index,
                labels_by_reader={"reader-a": label, "reader-b": label},
            )
        )
        common = {
            "schema_id": 1000 + index,
            "canonical_name": canonical,
            "normalized_name": retrieval_key(canonical),
            "statement_type": "CDKT",
            "display_order": index,
            "parent_id": None,
            "hierarchy_level": 1,
            "historical_aliases": [],
            "scope": ["SEPARATE", "CONSOLIDATED"],
        }
        base_items.append(SchemaItem(structural_aliases=[], **common))
        exact_items.append(
            SchemaItem(
                structural_aliases=[] if index < anchor_count else [alias],
                **common,
            )
        )

    sealed: list[dict[str, object]] = []
    for interval_index in range(anchor_count + 1):
        previous_anchor_index = interval_index - 1 if interval_index else None
        next_anchor_index = interval_index if interval_index < anchor_count else None
        trailing = range(anchor_count, total_count) if next_anchor_index is None else ()
        sealed.append(
            {
                "interval_index": interval_index,
                "previous_anchor_row_id": (
                    None if previous_anchor_index is None else f"row-{previous_anchor_index}"
                ),
                "previous_anchor_report_norm_id": (
                    None if previous_anchor_index is None else 1000 + previous_anchor_index
                ),
                "next_anchor_row_id": (
                    None if next_anchor_index is None else f"row-{next_anchor_index}"
                ),
                "next_anchor_report_norm_id": (
                    None if next_anchor_index is None else 1000 + next_anchor_index
                ),
                "row_ids": [f"row-{index}" for index in trailing],
                "report_norm_ids": [1000 + index for index in trailing],
            }
        )
    return (
        rows,
        build_schema_projection_v2(base_items, "CDKT"),
        build_schema_projection_v2(exact_items, "CDKT"),
        sealed,
    )


def _rows(row_count: int) -> list[SourceStructureRowV2]:
    return [
        SourceStructureRowV2(
            row_id=f"row-{index}",
            order=index,
            labels_by_reader={"single_reader": "shared component"},
            row_role="UNKNOWN",
            report_scope="UNKNOWN",
        )
        for index in range(row_count)
    ]


def _sealed_interval(row_count: int, node_count: int) -> list[dict[str, object]]:
    return [
        {
            "interval_index": 0,
            "previous_anchor_row_id": None,
            "previous_anchor_report_norm_id": None,
            "next_anchor_row_id": None,
            "next_anchor_report_norm_id": None,
            "row_ids": [f"row-{index}" for index in range(row_count)],
            "report_norm_ids": [1000 + index for index in range(node_count)],
        }
    ]


def test_six_by_nine_bound_is_the_e0037_audited_maximum():
    plan = plan_e0038_exact_search(_sealed_interval(6, 9))

    assert plan.eligible
    assert plan.status is None
    assert plan.maximum_monotone_signature_bound == 5005
    assert plan.maximum_monotone_signature_bound == E0037_MAX_MONOTONE_SIGNATURE_BOUND
    assert plan.interval_bounds[0].row_count == 6
    assert plan.interval_bounds[0].schema_node_count == 9
    assert plan.interval_bounds[0].cell_signature_sum_bound == 19447
    assert plan.interval_bounds[0].worst_case_search_multiplier == 7
    assert plan.interval_bounds[0].total_signature_work_bound == 136129
    assert plan.total_cell_signature_sum_bound == 19447
    assert plan.total_signature_work_bound == 136129
    assert plan.hard_cap == E0038_EXACT_SEARCH_HARD_CAP


@pytest.mark.parametrize(
    ("row_count", "node_count", "reported_bound", "expected_status"),
    [
        (6, 10, 8008, E0038ExactSearchStatus.ABSTAINED_E0037_BOUND_EXCEEDED),
        (7, 10, 8193, E0038ExactSearchStatus.ABSTAINED_HARD_CAP_EXCEEDED),
    ],
)
def test_over_bound_plans_fail_closed(
    row_count: int,
    node_count: int,
    reported_bound: int,
    expected_status: E0038ExactSearchStatus,
):
    plan = plan_e0038_exact_search(_sealed_interval(row_count, node_count))

    assert not plan.eligible
    assert plan.status is expected_status
    assert plan.maximum_monotone_signature_bound == reported_bound
    assert "aligner was not invoked" in plan.reason


def test_multiple_individually_bounded_intervals_exceed_total_work_cap():
    anchor_row = "anchor-row"
    anchor_id = 2000
    sealed = [
        {
            "interval_index": 0,
            "previous_anchor_row_id": None,
            "previous_anchor_report_norm_id": None,
            "next_anchor_row_id": anchor_row,
            "next_anchor_report_norm_id": anchor_id,
            "row_ids": [f"left-row-{index}" for index in range(6)],
            "report_norm_ids": [1000 + index for index in range(9)],
        },
        {
            "interval_index": 1,
            "previous_anchor_row_id": anchor_row,
            "previous_anchor_report_norm_id": anchor_id,
            "next_anchor_row_id": None,
            "next_anchor_report_norm_id": None,
            "row_ids": [f"right-row-{index}" for index in range(6)],
            "report_norm_ids": [3000 + index for index in range(9)],
        },
    ]

    plan = plan_e0038_exact_search(sealed)

    assert plan.status is E0038ExactSearchStatus.ABSTAINED_TOTAL_WORK_CAP_EXCEEDED
    assert plan.maximum_monotone_signature_bound == 5005
    assert plan.total_signature_work_bound == E0038_MAX_TOTAL_SIGNATURE_WORK + 1
    assert "aligner was not invoked" in plan.reason


@pytest.mark.parametrize("mutation", ["first", "last", "adjacent", "interior"])
def test_full_interval_chain_invariants_fail_closed(mutation: str):
    anchor_row = "anchor-row"
    anchor_id = 1001
    sealed = [
        {
            "interval_index": 0,
            "previous_anchor_row_id": None,
            "previous_anchor_report_norm_id": None,
            "next_anchor_row_id": anchor_row,
            "next_anchor_report_norm_id": anchor_id,
            "row_ids": ["row-0"],
            "report_norm_ids": [1000],
        },
        {
            "interval_index": 1,
            "previous_anchor_row_id": anchor_row,
            "previous_anchor_report_norm_id": anchor_id,
            "next_anchor_row_id": None,
            "next_anchor_report_norm_id": None,
            "row_ids": ["row-2"],
            "report_norm_ids": [1002],
        },
    ]
    if mutation == "first":
        sealed[0]["previous_anchor_row_id"] = "forged-first"
        sealed[0]["previous_anchor_report_norm_id"] = 999
    elif mutation == "last":
        sealed[-1]["next_anchor_row_id"] = "forged-last"
        sealed[-1]["next_anchor_report_norm_id"] = 1003
    elif mutation == "adjacent":
        sealed[1]["previous_anchor_row_id"] = "different-anchor"
    else:
        sealed[1]["row_ids"] = [anchor_row]

    plan = plan_e0038_exact_search(sealed)

    assert plan.status is E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT
    assert not plan.eligible
    assert "aligner was not invoked" in plan.reason


def test_policy_is_identical_to_e0037_except_for_beam(project_root: Path):
    baseline, exact = _policies(project_root)
    baseline_payload = yaml.safe_load(baseline.source_bytes)
    exact_payload = yaml.safe_load(exact.source_bytes)

    assert baseline.beam_width == 64
    assert exact.beam_width == 8192
    baseline_payload["search"]["beam_width_per_dp_cell"] = 8192
    assert baseline_payload == exact_payload
    validate_e0038_policy_parity(baseline, exact)

    changed_bytes = exact.source_bytes.replace(
        b"minimum_interval_best_runner_up_margin: 0.15",
        b"minimum_interval_best_runner_up_margin: 0.16",
    )
    changed = load_ordered_subgraph_v2_policy_bytes(
        changed_bytes,
        source_path=Path("changed-e0038-policy.yaml"),
    )
    with pytest.raises(E0038ExactSearchError, match="beyond beam_width_per_dp_cell"):
        validate_e0038_policy_parity(baseline, changed)


def test_policy_subclass_cannot_override_identity_comparison(project_root: Path):
    baseline, exact = _policies(project_root)

    class AlwaysEqualPolicy(OrderedSubgraphV2Policy):
        def __eq__(self, other):
            return True

    forged = AlwaysEqualPolicy(**baseline.__dict__)
    with pytest.raises(E0038ExactSearchError, match="invalid runtime types"):
        validate_e0038_policy_parity(forged, exact)


def test_policy_bytes_subclass_cannot_split_hash_from_decode(project_root: Path):
    baseline, exact = _policies(project_root)
    original = b"  minimum_interval_best_runner_up_margin: 0.15"
    mutated = b"  minimum_interval_best_runner_up_margin: 0.16"
    assert baseline.source_bytes.count(original) == 1

    class SplitIdentityBytes(bytes):
        def decode(self, *args, **kwargs):
            return (
                super()
                .decode(*args, **kwargs)
                .replace(
                    mutated.decode(),
                    original.decode(),
                )
            )

    forged_bytes = SplitIdentityBytes(baseline.source_bytes.replace(original, mutated, 1))
    forged = load_ordered_subgraph_v2_policy_bytes(
        forged_bytes,
        source_path=Path("forged-e0037-policy.yaml"),
    )
    assert forged.minimum_interval_margin == baseline.minimum_interval_margin
    assert forged.policy_sha256 == hashlib.sha256(forged_bytes).hexdigest()
    assert forged.policy_sha256 != baseline.policy_sha256

    with pytest.raises(E0038ExactSearchError, match="invalid runtime types"):
        validate_e0038_policy_parity(forged, exact)


def test_six_by_nine_dense_search_has_zero_pruning(project_root: Path):
    baseline, exact = _policies(project_root)
    rows = _rows(6)
    projection = _projection(9)

    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(6, 9),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.EXACT_SEARCH_COMPLETE
    assert outcome.align_invocation_count == 1
    assert outcome.plan.maximum_monotone_signature_bound == 5005
    assert outcome.main_search_pruned_states == 0
    assert outcome.counterfactual_search_pruned_states == 0
    assert outcome.result is not None
    assert outcome.result.search.pruned_states == 0
    assert all(interval.search_exhaustive for interval in outcome.result.intervals)


def test_exact_alias_partition_is_the_executed_partition_authority(project_root: Path):
    baseline, exact = _policies(project_root)
    base_projection = _named_projection("unrelated liability")
    alias_projection = _named_projection(
        "unrelated liability",
        aliases=("shared component",),
    )
    rows = [
        SourceStructureRowV2(
            row_id="row-0",
            order=0,
            labels_by_reader={
                "reader-a": "shared component",
                "reader-b": "shared component",
            },
        )
    ]

    outcome = run_e0038_exact_search(
        rows,
        alias_projection,
        base_projection=base_projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.EXACT_SEARCH_COMPLETE
    assert outcome.result is not None
    assert len(outcome.plan.interval_bounds) == 2
    assert len(outcome.result.intervals) == 2
    assert all(item.row_count == 0 for item in outcome.plan.interval_bounds)
    assert all(item.schema_node_count == 0 for item in outcome.plan.interval_bounds)
    assert outcome.plan.interval_bounds[0].next_anchor_row_id == "row-0"
    assert outcome.plan.interval_bounds[0].next_anchor_report_norm_id == 1000
    assert outcome.result.row_mappings[0].selected_report_norm_id == 1000


def test_exact_alias_partition_can_change_40_intervals_to_42(project_root: Path):
    baseline, exact = _policies(project_root)
    rows, base_projection, alias_projection, sealed = _forty_to_forty_two_case()

    outcome = run_e0038_exact_search(
        rows,
        alias_projection,
        base_projection=base_projection,
        sealed_interval_diagnostics=sealed,
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert len(sealed) == 40
    assert outcome.status is E0038ExactSearchStatus.EXACT_SEARCH_COMPLETE
    assert outcome.result is not None
    assert len(outcome.plan.interval_bounds) == 42
    assert len(outcome.result.intervals) == 42


def test_rows_are_canonically_frozen_before_aligner(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)
    labels = {"single_reader": "shared component"}
    rows = [
        SourceStructureRowV2(
            row_id="row-0",
            order=0,
            labels_by_reader=labels,
        )
    ]
    projection = _projection(1)
    immutable_aligner = align_ordered_subgraph_v2

    def mutating_caller(received_rows, received_projection, *, policy):
        labels["single_reader"] = "hostile mutation"
        assert received_rows[0].labels_by_reader["single_reader"] == "shared component"
        with pytest.raises(TypeError):
            received_rows[0].labels_by_reader["single_reader"] = "second mutation"
        return immutable_aligner(received_rows, received_projection, policy=policy)

    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", mutating_caller)
    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert labels == {"single_reader": "hostile mutation"}
    assert outcome.status is E0038ExactSearchStatus.EXACT_SEARCH_COMPLETE
    assert outcome.result is not None


def test_over_bound_wrapper_does_not_invoke_aligner(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)

    def forbidden_aligner(*args, **kwargs):
        raise AssertionError("aligner must not run for an over-bound plan")

    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", forbidden_aligner)
    outcome = run_e0038_exact_search(
        _rows(1),
        _projection(1),
        base_projection=_projection(1),
        sealed_interval_diagnostics=_sealed_interval(6, 10),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_E0037_BOUND_EXCEEDED
    assert outcome.align_invocation_count == 0
    assert outcome.result is None


def test_small_seal_cannot_hide_larger_actual_partition(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)

    def forbidden_aligner(*args, **kwargs):
        raise AssertionError("aligner must not run before actual partition validation")

    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", forbidden_aligner)
    projection = _projection(10)
    outcome = run_e0038_exact_search(
        _rows(7),
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT
    assert outcome.align_invocation_count == 0
    assert outcome.result is None


def test_postrun_interval_identity_drift_withholds_mapping_result(project_root: Path):
    baseline, exact = _policies(project_root)
    sealed = _sealed_interval(1, 1)
    sealed[0]["row_ids"] = ["different-sealed-row"]

    outcome = run_e0038_exact_search(
        _rows(1),
        _projection(1),
        base_projection=_projection(1),
        sealed_interval_diagnostics=sealed,
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT
    assert outcome.align_invocation_count == 0
    assert outcome.result is None


def test_postrun_nonzero_pruning_withholds_mapping_result(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)
    rows = _rows(1)
    projection = _projection(1)
    real_result = align_ordered_subgraph_v2(rows, projection, policy=exact)
    bad_interval = replace(
        real_result.intervals[0],
        main_search_pruned_states=1,
        search_exhaustive=False,
    )
    bad_search = replace(
        real_result.search,
        pruned_states=1,
        main_search_pruned_states=1,
    )
    pruned_result = replace(
        real_result,
        intervals=(bad_interval,),
        search=bad_search,
    )
    monkeypatch.setattr(
        exact_search,
        "align_ordered_subgraph_v2",
        lambda *args, **kwargs: pruned_result,
    )

    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_NONZERO_PRUNING
    assert outcome.align_invocation_count == 1
    assert outcome.main_search_pruned_states == 1
    assert outcome.counterfactual_search_pruned_states == 0
    assert outcome.result is None


def test_full_boundary_chain_is_verified_before_aligner(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)
    sealed = [
        {
            "interval_index": 0,
            "previous_anchor_row_id": None,
            "previous_anchor_report_norm_id": None,
            "next_anchor_row_id": "row-0",
            "next_anchor_report_norm_id": 1000,
            "row_ids": [],
            "report_norm_ids": [],
        },
        {
            "interval_index": 1,
            "previous_anchor_row_id": "row-0",
            "previous_anchor_report_norm_id": 1000,
            "next_anchor_row_id": None,
            "next_anchor_report_norm_id": None,
            "row_ids": [],
            "report_norm_ids": [],
        },
    ]

    def forbidden_aligner(*args, **kwargs):
        raise AssertionError("aligner must not run for a forged boundary chain")

    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", forbidden_aligner)
    outcome = run_e0038_exact_search(
        _rows(1),
        _projection(1),
        base_projection=_projection(1),
        sealed_interval_diagnostics=sealed,
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT
    assert outcome.align_invocation_count == 0
    assert outcome.result is None


def test_per_interval_negative_pruning_cannot_cancel_positive_pruning(
    project_root: Path, monkeypatch
):
    baseline, exact = _policies(project_root)
    rows = [
        SourceStructureRowV2(
            row_id="row-0",
            order=0,
            labels_by_reader={
                "reader-a": "shared component",
                "reader-b": "shared component",
            },
        )
    ]
    projection = _named_projection("shared component")
    real_result = align_ordered_subgraph_v2(rows, projection, policy=exact)
    assert len(real_result.intervals) == 2
    bad_intervals = (
        replace(
            real_result.intervals[0],
            main_search_pruned_states=1,
            search_exhaustive=False,
        ),
        replace(real_result.intervals[1], main_search_pruned_states=-1),
    )
    bad_result = replace(real_result, intervals=bad_intervals)
    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", lambda *a, **k: bad_result)

    sealed = [
        {
            "interval_index": 0,
            "previous_anchor_row_id": None,
            "previous_anchor_report_norm_id": None,
            "next_anchor_row_id": "row-0",
            "next_anchor_report_norm_id": 1000,
            "row_ids": [],
            "report_norm_ids": [],
        },
        {
            "interval_index": 1,
            "previous_anchor_row_id": "row-0",
            "previous_anchor_report_norm_id": 1000,
            "next_anchor_row_id": None,
            "next_anchor_report_norm_id": None,
            "row_ids": [],
            "report_norm_ids": [],
        },
    ]

    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=sealed,
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_NONZERO_PRUNING
    assert outcome.result is None


def test_malformed_interval_counter_abstains_before_sum(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)
    rows = _rows(1)
    projection = _projection(1)
    real_result = align_ordered_subgraph_v2(rows, projection, policy=exact)
    malformed_interval = replace(
        real_result.intervals[0],
        main_search_pruned_states="1",
    )
    malformed_result = replace(real_result, intervals=(malformed_interval,))
    monkeypatch.setattr(
        exact_search,
        "align_ordered_subgraph_v2",
        lambda *args, **kwargs: malformed_result,
    )

    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_NONZERO_PRUNING
    assert outcome.main_search_pruned_states == 0
    assert outcome.counterfactual_search_pruned_states == 0
    assert outcome.result is None


def test_stale_beam_64_result_is_rejected(project_root: Path, monkeypatch):
    baseline, exact = _policies(project_root)
    rows = _rows(1)
    projection = _projection(1)
    stale = align_ordered_subgraph_v2(rows, projection, policy=baseline)
    monkeypatch.setattr(exact_search, "align_ordered_subgraph_v2", lambda *a, **k: stale)

    outcome = run_e0038_exact_search(
        rows,
        projection,
        base_projection=projection,
        sealed_interval_diagnostics=_sealed_interval(1, 1),
        e0037_policy=baseline,
        exact_policy=exact,
    )

    assert outcome.status is E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT
    assert outcome.result is None


def test_hostile_diagnostic_sizes_fail_before_combination_math():
    sealed = _sealed_interval(0, 0)
    sealed[0]["report_norm_ids"] = list(range(1, 100_002))

    with pytest.raises(E0038ExactSearchError, match="schema-node budget"):
        plan_e0038_exact_search(sealed)


def test_dense_one_by_5004_fails_before_combination_math():
    sealed = _sealed_interval(1, 0)
    sealed[0]["report_norm_ids"] = list(range(1, 5005))

    with pytest.raises(E0038ExactSearchError, match="schema-node budget"):
        plan_e0038_exact_search(sealed)


def test_projection_node_budget_fails_before_sort_or_digest():
    projection = _projection(78)

    with pytest.raises(E0038ExactSearchError, match="schema budget"):
        exact_search._freeze_projection(projection)


def test_generic_container_subclasses_cannot_bypass_resource_caps():
    class LyingRows:
        def __len__(self):
            return 1

        def __getitem__(self, index):
            if index >= 65:
                raise IndexError
            return _rows(1)[0]

    class ForgedLabels(dict):
        pass

    with pytest.raises(E0038ExactSearchError, match="concrete sequence"):
        exact_search._freeze_rows(LyingRows())

    row = replace(_rows(1)[0], labels_by_reader=ForgedLabels({"reader": "label"}))
    with pytest.raises(E0038ExactSearchError, match="concrete mapping"):
        exact_search._freeze_rows([row])


def test_projection_nested_budget_and_foreign_nodes_fail_before_digest():
    projection = _projection(1)
    oversized_node = replace(projection.nodes[0], structural_aliases=("alias",) * 33)
    oversized = replace(projection, nodes=(oversized_node,))
    with pytest.raises(E0038ExactSearchError, match="nested sequence budget"):
        exact_search._freeze_projection(oversized)

    class ForeignNode(SchemaProjectionNodeV2):
        pass

    foreign_node = ForeignNode(**projection.nodes[0].__dict__)
    foreign = replace(projection, nodes=(foreign_node,))
    with pytest.raises(E0038ExactSearchError, match="foreign node"):
        exact_search._freeze_projection(foreign)
