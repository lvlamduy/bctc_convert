from __future__ import annotations

import inspect
from dataclasses import replace
from hashlib import sha256

import pytest

from bctc_ai.evaluation.incremental_formal_dag_v1 import (
    CacheDecisionV1,
    ContentRefKindV1,
    CoverageKindV1,
    CurrentDocumentRefsV1,
    FormalStageV1,
    PageCoverageBoundV1,
    PlanModeV1,
    StageOutcomeV1,
    StagePinsV1,
    StageReceiptV1,
    TypedContentRefV1,
    build_stage_receipt_v1,
    plan_incremental_formal_dag_v1,
)
from bctc_ai.evaluation.incremental_formal_runtime_v2 import (
    FailureLedgerStateV2,
    FailureTaxonomyV2,
    IncrementalFormalRuntimeV2Error,
    LifecycleActionV2,
    ReleaseAuthorityV2,
    RuntimeObservationKindV2,
    RuntimeScopeV2,
    append_stage_failure_v2,
    append_targeted_success_v2,
    build_caller_current_refs_v2,
    build_runtime_preflight_v2,
    build_targeted_stage_receipt_v2,
    build_verified_empty_failure_ledger_v2,
    plan_incremental_formal_runtime_v2,
    validate_failure_ledger_v2,
)

_FAMILY = "TEST_ACCOUNTING_FAMILY"


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _ref(kind: ContentRefKindV1, logical_id: str, revision: str) -> TypedContentRefV1:
    return TypedContentRefV1(kind, logical_id, _digest(f"{logical_id}:{revision}"), len(revision))


def _documents(count: int) -> tuple[CurrentDocumentRefsV1, ...]:
    return tuple(
        CurrentDocumentRefsV1(
            ordinal,
            f"doc-{ordinal:03d}",
            _ref(ContentRefKindV1.DOCUMENT_PACKET, f"packet-{ordinal:03d}", "v1"),
            _ref(ContentRefKindV1.SOURCE_PDF, f"pdf-{ordinal:03d}", "v1"),
            _ref(ContentRefKindV1.PAGE_SET, f"pages-{ordinal:03d}", "v1"),
            3,
        )
        for ordinal in range(1, count + 1)
    )


def _pins(*, graph_spec: str = "graph-v1", prompt: str = "prompt-v1") -> dict[
    FormalStageV1, StagePinsV1
]:
    def code(stage: FormalStageV1) -> TypedContentRefV1:
        return _ref(ContentRefKindV1.CODE, f"code/{stage.value.lower()}", "v1")

    def spec(stage: FormalStageV1, revision: str = "v1") -> TypedContentRefV1:
        return _ref(ContentRefKindV1.SPEC, f"spec/{stage.value.lower()}", revision)

    return {
        FormalStageV1.SOURCE: StagePinsV1((code(FormalStageV1.SOURCE),)),
        FormalStageV1.NORMALIZED_SPANS: StagePinsV1(
            (code(FormalStageV1.NORMALIZED_SPANS),)
        ),
        FormalStageV1.RETRIEVAL: StagePinsV1(
            (code(FormalStageV1.RETRIEVAL),),
            (spec(FormalStageV1.RETRIEVAL),),
        ),
        FormalStageV1.GRAPH: StagePinsV1(
            (code(FormalStageV1.GRAPH),),
            (spec(FormalStageV1.GRAPH, graph_spec),),
        ),
        FormalStageV1.GEMMA_RESCUE: StagePinsV1(
            (code(FormalStageV1.GEMMA_RESCUE),),
            (),
            (_ref(ContentRefKindV1.MODEL, "model/gemma", "v1"),),
            (_ref(ContentRefKindV1.PROMPT, "prompt/gemma", prompt),),
        ),
        FormalStageV1.NUMERIC_PIXEL: StagePinsV1(
            (code(FormalStageV1.NUMERIC_PIXEL),),
            (spec(FormalStageV1.NUMERIC_PIXEL),),
        ),
        FormalStageV1.MAPPING: StagePinsV1(
            (code(FormalStageV1.MAPPING),),
            (spec(FormalStageV1.MAPPING),),
        ),
        FormalStageV1.SEAL: StagePinsV1(
            (code(FormalStageV1.SEAL),),
            (spec(FormalStageV1.SEAL),),
        ),
    }


def _outcome(stage: FormalStageV1) -> StageOutcomeV1:
    return {
        FormalStageV1.SOURCE: StageOutcomeV1.SOURCE_READY,
        FormalStageV1.NORMALIZED_SPANS: StageOutcomeV1.NORMALIZED_SPANS_READY,
        FormalStageV1.RETRIEVAL: StageOutcomeV1.RETRIEVAL_HIT,
        FormalStageV1.GRAPH: StageOutcomeV1.GRAPH_RESOLVED,
        FormalStageV1.GEMMA_RESCUE: StageOutcomeV1.GEMMA_RESOLVED,
        FormalStageV1.NUMERIC_PIXEL: StageOutcomeV1.NUMERIC_VERIFIED,
        FormalStageV1.MAPPING: StageOutcomeV1.MAPPING_RESOLVED,
        FormalStageV1.SEAL: StageOutcomeV1.SEALED,
    }[stage]


def _coverage(
    stage: FormalStageV1, document: CurrentDocumentRefsV1
) -> PageCoverageBoundV1 | None:
    if stage is not FormalStageV1.RETRIEVAL:
        return None
    return PageCoverageBoundV1(
        CoverageKindV1.BOUNDED_POSITIVE_SHORTLIST,
        document.page_set_ref,
        document.page_count,
        2,
    )


def _complete_cache(
    documents: tuple[CurrentDocumentRefsV1, ...],
    pins: dict[FormalStageV1, StagePinsV1],
) -> tuple[StageReceiptV1, ...]:
    by_id = {item.document_id: item for item in documents}
    receipts: tuple[StageReceiptV1, ...] = ()
    for _round in range(8):
        plan = plan_incremental_formal_dag_v1(
            mode=PlanModeV1.RELEASE_SEAL,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
        )
        if plan.ready:
            return receipts
        assert plan.runnable
        additions = tuple(
            build_stage_receipt_v1(
                item,
                page_count=by_id[item.document_id].page_count,
                output_sha256=_digest(f"{item.expected_stage_key}:stable-output"),
                output_size_bytes=31,
                outcome=_outcome(item.stage),
                coverage_bound=_coverage(item.stage, by_id[item.document_id]),
            )
            for item in plan.runnable
        )
        receipts = (*receipts, *additions)
    raise AssertionError("synthetic V1 cache did not converge")


def _without_graph(
    receipts: tuple[StageReceiptV1, ...], document_id: str
) -> tuple[StageReceiptV1, ...]:
    return tuple(
        item
        for item in receipts
        if not (item.document_id == document_id and item.stage is FormalStageV1.GRAPH)
    )


def _decision(plan, document_id: str, stage: FormalStageV1):
    return next(
        item for item in plan.decisions if item.document_id == document_id and item.stage is stage
    )


def _preflight(
    *,
    scope: RuntimeScopeV2,
    selected: tuple[str, ...],
    documents: tuple[CurrentDocumentRefsV1, ...],
    pins: dict[FormalStageV1, StagePinsV1],
    receipts: tuple[StageReceiptV1, ...],
    ledger,
):
    return build_runtime_preflight_v2(
        family_id=_FAMILY,
        scope=scope,
        selected_document_ids=selected,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        failure_ledger=ledger,
    )


def _dev_plan(
    *,
    scope: RuntimeScopeV2,
    selected: tuple[str, ...],
    documents: tuple[CurrentDocumentRefsV1, ...],
    pins: dict[FormalStageV1, StagePinsV1],
    receipts: tuple[StageReceiptV1, ...],
    ledger,
):
    flight = _preflight(
        scope=scope,
        selected=selected,
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    plan = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=flight,
        dev_document_ids=selected,
    )
    return flight, plan


def _targeted_receipt(
    planned_stage,
    original: StageReceiptV1,
    document: CurrentDocumentRefsV1,
) -> StageReceiptV1:
    return build_targeted_stage_receipt_v2(
        planned_stage,
        page_count=document.page_count,
        output_sha256=original.output_ref.sha256,
        output_size_bytes=original.output_ref.size_bytes,
        outcome=original.outcome,
        coverage_bound=original.coverage_bound,
    )


def test_failure_ledger_is_mandatory_verified_empty_or_closed_and_exact_typed() -> None:
    documents = _documents(1)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    assert ledger.state is FailureLedgerStateV2.VERIFIED_EMPTY
    assert not ledger.observations

    signature = inspect.signature(plan_incremental_formal_runtime_v2)
    assert signature.parameters["failure_ledger"].default is inspect.Parameter.empty
    assert signature.parameters["preflight"].default is inspect.Parameter.empty

    exact_type_tamper = replace(
        ledger,
        counters=replace(ledger.counters, stage_failure_count=False),
    )
    with pytest.raises(IncrementalFormalRuntimeV2Error, match="exact integer"):
        validate_failure_ledger_v2(exact_type_tamper)

    with pytest.raises(IncrementalFormalRuntimeV2Error, match="identity/scope"):
        build_runtime_preflight_v2(
            family_id=_FAMILY,
            scope=RuntimeScopeV2.FOCUSED,
            selected_document_ids=[documents[0].document_id],
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
            failure_ledger=ledger,
        )


def test_append_only_failure_then_fresh_targeted_success_converges() -> None:
    documents = _documents(2)
    pins = _pins()
    complete = _complete_cache(documents, pins)
    original_graph = next(
        item
        for item in complete
        if item.document_id == "doc-001" and item.stage is FormalStageV1.GRAPH
    )
    receipts = _without_graph(complete, "doc-001")
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)

    focused, initial = _dev_plan(
        scope=RuntimeScopeV2.FOCUSED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    graph = _decision(initial, "doc-001", FormalStageV1.GRAPH)
    assert graph.decision is CacheDecisionV1.RECOMPUTE
    ledger = append_stage_failure_v2(
        ledger,
        graph,
        preflight=focused,
        taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
        observed_runtime_ms=1_000,
    )

    targeted, retry = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    retry_graph = _decision(retry, "doc-001", FormalStageV1.GRAPH)
    assert retry_graph.lifecycle_action is LifecycleActionV2.TARGETED_RETRY_REQUIRED
    fresh_receipt = _targeted_receipt(retry_graph, original_graph, documents[0])
    ledger = append_targeted_success_v2(
        ledger,
        retry_graph,
        preflight=targeted,
        result_receipt=fresh_receipt,
        observed_runtime_ms=2_000,
    )
    receipts = (*receipts, fresh_receipt)

    _, converged = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    assert converged.ready
    assert not converged.runnable
    assert converged.historical_counters.stage_failure_count == 1
    assert converged.historical_counters.targeted_success_count == 1
    assert ledger.state is FailureLedgerStateV2.CLOSED
    assert len(ledger.observations) == 2


def test_success_never_erases_repeat_counter_or_same_revision_review_latch() -> None:
    documents = _documents(2)
    pins = _pins()
    complete = _complete_cache(documents, pins)
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)

    graph_a_original = next(
        item
        for item in complete
        if item.document_id == "doc-001" and item.stage is FormalStageV1.GRAPH
    )
    receipts = _without_graph(complete, "doc-001")
    focused, first_plan = _dev_plan(
        scope=RuntimeScopeV2.FOCUSED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    ledger = append_stage_failure_v2(
        ledger,
        _decision(first_plan, "doc-001", FormalStageV1.GRAPH),
        preflight=focused,
        taxonomy=FailureTaxonomyV2.COLUMN_AXIS,
        observed_runtime_ms=100,
    )
    targeted, retry = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    retry_graph = _decision(retry, "doc-001", FormalStageV1.GRAPH)
    fresh = _targeted_receipt(retry_graph, graph_a_original, documents[0])
    ledger = append_targeted_success_v2(
        ledger,
        retry_graph,
        preflight=targeted,
        result_receipt=fresh,
        observed_runtime_ms=100,
    )
    receipts = (*receipts, fresh)

    receipts_b = _without_graph(receipts, "doc-002")
    focused_b, second_plan = _dev_plan(
        scope=RuntimeScopeV2.FOCUSED,
        selected=("doc-002",),
        documents=documents,
        pins=pins,
        receipts=receipts_b,
        ledger=ledger,
    )
    ledger = append_stage_failure_v2(
        ledger,
        _decision(second_plan, "doc-002", FormalStageV1.GRAPH),
        preflight=focused_b,
        taxonomy=FailureTaxonomyV2.COLUMN_AXIS,
        observed_runtime_ms=100,
    )

    targeted_b, blocked = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-002",),
        documents=documents,
        pins=pins,
        receipts=receipts_b,
        ledger=ledger,
    )
    del targeted_b
    blocked_graph = _decision(blocked, "doc-002", FormalStageV1.GRAPH)
    assert blocked_graph.decision is CacheDecisionV1.BLOCKED
    assert (
        blocked_graph.lifecycle_action
        is LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE
    )
    assert blocked.algorithm_review_required
    assert blocked.historical_counters.stage_failure_count == 2
    assert blocked.historical_counters.targeted_success_count == 1


def test_family_hard_budget_breach_above_300_seconds_blocks_equivalent_revision_once() -> None:
    documents = _documents(140)
    pins = _pins()
    complete = _complete_cache(documents, pins)
    receipts = _without_graph(complete, "doc-001")
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    selected = tuple(item.document_id for item in documents)
    flight = _preflight(
        scope=RuntimeScopeV2.FAMILY_140_COLD,
        selected=selected,
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    plan = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=flight,
    )
    ledger = append_stage_failure_v2(
        ledger,
        _decision(plan, "doc-001", FormalStageV1.GRAPH),
        preflight=flight,
        taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
        observed_runtime_ms=300_001,
    )

    next_flight = _preflight(
        scope=RuntimeScopeV2.FAMILY_140_COLD,
        selected=selected,
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    blocked = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=next_flight,
    )
    graph_decisions = tuple(item for item in blocked.decisions if item.stage is FormalStageV1.GRAPH)
    assert len(graph_decisions) == 140
    assert all(item.decision is CacheDecisionV1.BLOCKED for item in graph_decisions)
    assert all(
        item.lifecycle_action is LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_HARD_BUDGET
        for item in graph_decisions
    )
    assert not any(item.stage is FormalStageV1.GRAPH for item in blocked.runnable)
    assert ledger.observations[-1].kind is RuntimeObservationKindV2.HARD_BUDGET_BREACH


def test_one_family_target_breach_allows_one_profiled_retry_then_review() -> None:
    documents = _documents(140)
    pins = _pins()
    complete = _complete_cache(documents, pins)
    receipts = _without_graph(complete, "doc-001")
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    selected = tuple(item.document_id for item in documents)
    cold = _preflight(
        scope=RuntimeScopeV2.FAMILY_140_COLD,
        selected=selected,
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    cold_plan = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=cold,
    )
    ledger = append_stage_failure_v2(
        ledger,
        _decision(cold_plan, "doc-001", FormalStageV1.GRAPH),
        preflight=cold,
        taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
        observed_runtime_ms=180_001,
    )
    targeted, retry = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    retry_graph = _decision(retry, "doc-001", FormalStageV1.GRAPH)
    assert retry_graph.lifecycle_action is LifecycleActionV2.TARGETED_RETRY_REQUIRED
    ledger = append_stage_failure_v2(
        ledger,
        retry_graph,
        preflight=targeted,
        taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
        observed_runtime_ms=1_000,
    )

    _, reviewed = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    reviewed_graph = _decision(reviewed, "doc-001", FormalStageV1.GRAPH)
    assert reviewed_graph.decision is CacheDecisionV1.BLOCKED
    assert (
        reviewed_graph.lifecycle_action
        is LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_TARGET_BUDGET
    )
    assert reviewed.historical_counters.target_budget_breach_count == 1
    assert reviewed.historical_counters.stage_failure_count == 1


def test_revision_probation_runs_only_implicated_document_before_corpus_opens() -> None:
    documents = _documents(2)
    pins_v1 = _pins(graph_spec="graph-v1")
    complete = _complete_cache(documents, pins_v1)
    original_graph = next(
        item
        for item in complete
        if item.document_id == "doc-001" and item.stage is FormalStageV1.GRAPH
    )
    receipts = _without_graph(complete, "doc-001")
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    focused, initial = _dev_plan(
        scope=RuntimeScopeV2.FOCUSED,
        selected=("doc-001",),
        documents=documents,
        pins=pins_v1,
        receipts=receipts,
        ledger=ledger,
    )
    ledger = append_stage_failure_v2(
        ledger,
        _decision(initial, "doc-001", FormalStageV1.GRAPH),
        preflight=focused,
        taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
        observed_runtime_ms=10_000,
    )
    pins_v2 = _pins(graph_spec="graph-v2")

    targeted_a, probation_a = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-001",),
        documents=documents,
        pins=pins_v2,
        receipts=receipts,
        ledger=ledger,
    )
    graph_a = _decision(probation_a, "doc-001", FormalStageV1.GRAPH)
    assert graph_a.decision is CacheDecisionV1.RECOMPUTE
    assert graph_a.lifecycle_action is LifecycleActionV2.REVISION_PROBATION_REQUIRED

    _, unaffected_while_pending = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-002",),
        documents=documents,
        pins=pins_v2,
        receipts=receipts,
        ledger=ledger,
    )
    graph_b_pending = _decision(
        unaffected_while_pending, "doc-002", FormalStageV1.GRAPH
    )
    assert graph_b_pending.decision is CacheDecisionV1.BLOCKED
    assert (
        graph_b_pending.lifecycle_action
        is LifecycleActionV2.REVISION_PROBATION_PENDING_ELSEWHERE
    )

    fresh_v2 = _targeted_receipt(graph_a, original_graph, documents[0])
    ledger = append_targeted_success_v2(
        ledger,
        graph_a,
        preflight=targeted_a,
        result_receipt=fresh_v2,
        observed_runtime_ms=1_000,
    )
    receipts = (*receipts, fresh_v2)
    _, opened = _dev_plan(
        scope=RuntimeScopeV2.TARGETED,
        selected=("doc-002",),
        documents=documents,
        pins=pins_v2,
        receipts=receipts,
        ledger=ledger,
    )
    graph_b = _decision(opened, "doc-002", FormalStageV1.GRAPH)
    assert graph_b.decision is CacheDecisionV1.RECOMPUTE
    assert graph_b.lifecycle_action is LifecycleActionV2.BASE_DAG_DECISION
    assert opened.historical_counters.hard_budget_breach_count == 1
    assert opened.historical_counters.targeted_success_count == 1


def test_preflight_binds_algorithm_spec_model_prompt_and_exact_milliseconds() -> None:
    documents = _documents(1)
    pins = _pins()
    complete = _complete_cache(documents, pins)
    receipts = _without_graph(complete, "doc-001")
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    focused, plan = _dev_plan(
        scope=RuntimeScopeV2.FOCUSED,
        selected=("doc-001",),
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    graph = _decision(plan, "doc-001", FormalStageV1.GRAPH)
    with pytest.raises(IncrementalFormalRuntimeV2Error, match="exact integer"):
        append_stage_failure_v2(
            ledger,
            graph,
            preflight=focused,
            taxonomy=FailureTaxonomyV2.ROW_TOPOLOGY,
            observed_runtime_ms=True,
        )
    with pytest.raises(IncrementalFormalRuntimeV2Error, match="closed non-runtime"):
        append_stage_failure_v2(
            ledger,
            graph,
            preflight=focused,
            taxonomy="ROW_TOPOLOGY",
            observed_runtime_ms=1,
        )

    changed_pins = _pins(prompt="prompt-v2")
    with pytest.raises(IncrementalFormalRuntimeV2Error, match="preflight is stale"):
        plan_incremental_formal_runtime_v2(
            mode=PlanModeV1.DEV_FAST,
            current_documents=documents,
            stage_pins=changed_pins,
            cached_receipts=receipts,
            family_id=_FAMILY,
            failure_ledger=ledger,
            preflight=focused,
            dev_document_ids=("doc-001",),
        )


def test_release_is_non_authoritative_without_exact_caller_current_refs() -> None:
    documents = _documents(140)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    ledger = build_verified_empty_failure_ledger_v2(family_id=_FAMILY)
    selected = tuple(item.document_id for item in documents)
    flight = _preflight(
        scope=RuntimeScopeV2.FAMILY_140_COLD,
        selected=selected,
        documents=documents,
        pins=pins,
        receipts=receipts,
        ledger=ledger,
    )
    missing = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=flight,
    )
    assert missing.execution_ready
    assert not missing.ready
    assert (
        missing.release_authority
        is ReleaseAuthorityV2.NON_AUTHORITATIVE_MISSING_CALLER_CURRENT_REFS
    )

    current_refs = build_caller_current_refs_v2(
        current_documents=documents,
        cached_receipts=receipts,
        failure_ledger=ledger,
    )
    bound = plan_incremental_formal_runtime_v2(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY,
        failure_ledger=ledger,
        preflight=flight,
        caller_current_refs=current_refs,
    )
    assert bound.ready
    assert (
        bound.release_authority
        is ReleaseAuthorityV2.CALLER_CURRENT_BOUND_RELEASE_CANDIDATE
    )
