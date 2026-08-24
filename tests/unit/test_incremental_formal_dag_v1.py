from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from bctc_ai.evaluation.incremental_formal_dag_v1 import (
    ATTEMPT_CLAIM_BOUNDARY,
    RECEIPT_CLAIM_BOUNDARY,
    AttemptKindV1,
    CacheDecisionV1,
    ContentRefKindV1,
    CoverageKindV1,
    CurrentDocumentRefsV1,
    DependencyRefV1,
    FormalStageV1,
    IncrementalFormalDagV1Error,
    PageCoverageBoundV1,
    PlanModeV1,
    PlannedStageV1,
    StageAttemptObservationV1,
    StageOutcomeV1,
    StagePinsV1,
    StageReceiptV1,
    TypedContentRefV1,
    build_stage_attempt_observation_v1,
    build_stage_receipt_v1,
    plan_incremental_formal_dag_v1,
    stage_invalidation_closure_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _ref(kind: ContentRefKindV1, logical_id: str, revision: str) -> TypedContentRefV1:
    return TypedContentRefV1(kind, logical_id, _digest(f"{logical_id}:{revision}"), len(revision))


def _documents(count: int = 1) -> tuple[CurrentDocumentRefsV1, ...]:
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


def _pins(
    *,
    retrieval_spec: str = "aliases-v1",
    numeric_code: str = "numeric-v1",
    gemma_model: str = "gemma-model-v1",
    gemma_prompt: str = "gemma-prompt-v1",
    graph_spec: str = "graph-spec-v1",
) -> dict[FormalStageV1, StagePinsV1]:
    def code(stage: FormalStageV1, revision: str | None = None) -> TypedContentRefV1:
        return _ref(ContentRefKindV1.CODE, f"code/{stage.value.lower()}", revision or "v1")

    def spec(stage: FormalStageV1, revision: str) -> TypedContentRefV1:
        return _ref(ContentRefKindV1.SPEC, f"spec/{stage.value.lower()}", revision)

    return {
        FormalStageV1.SOURCE: StagePinsV1((code(FormalStageV1.SOURCE),)),
        FormalStageV1.NORMALIZED_SPANS: StagePinsV1((code(FormalStageV1.NORMALIZED_SPANS),)),
        FormalStageV1.RETRIEVAL: StagePinsV1(
            (code(FormalStageV1.RETRIEVAL),),
            (spec(FormalStageV1.RETRIEVAL, retrieval_spec),),
        ),
        FormalStageV1.GRAPH: StagePinsV1(
            (code(FormalStageV1.GRAPH),),
            (spec(FormalStageV1.GRAPH, graph_spec),),
        ),
        FormalStageV1.GEMMA_RESCUE: StagePinsV1(
            (code(FormalStageV1.GEMMA_RESCUE),),
            (),
            (_ref(ContentRefKindV1.MODEL, "model/gemma", gemma_model),),
            (_ref(ContentRefKindV1.PROMPT, "prompt/gemma-structure", gemma_prompt),),
        ),
        FormalStageV1.NUMERIC_PIXEL: StagePinsV1(
            (code(FormalStageV1.NUMERIC_PIXEL, numeric_code),),
            (spec(FormalStageV1.NUMERIC_PIXEL, "numeric-spec-v1"),),
        ),
        FormalStageV1.MAPPING: StagePinsV1(
            (code(FormalStageV1.MAPPING),),
            (spec(FormalStageV1.MAPPING, "schema-v1"),),
        ),
        FormalStageV1.SEAL: StagePinsV1(
            (code(FormalStageV1.SEAL),),
            (spec(FormalStageV1.SEAL, "release-policy-v1"),),
        ),
    }


def _decision(
    decisions: tuple[PlannedStageV1, ...], document_id: str, stage: FormalStageV1
) -> PlannedStageV1:
    return next(
        item for item in decisions if item.document_id == document_id and item.stage is stage
    )


def _outcome(
    stage: FormalStageV1,
    document_id: str,
    *,
    rescue_documents: frozenset[str],
    absent_documents: frozenset[str],
    zero_hit_documents: frozenset[str],
) -> StageOutcomeV1:
    if stage is FormalStageV1.SOURCE:
        return StageOutcomeV1.SOURCE_READY
    if stage is FormalStageV1.NORMALIZED_SPANS:
        return StageOutcomeV1.NORMALIZED_SPANS_READY
    if stage is FormalStageV1.RETRIEVAL:
        return (
            StageOutcomeV1.RETRIEVAL_ZERO_HIT
            if document_id in zero_hit_documents
            else StageOutcomeV1.RETRIEVAL_HIT
        )
    if stage is FormalStageV1.GRAPH:
        if document_id in absent_documents:
            return StageOutcomeV1.GRAPH_NOT_OBSERVED
        if document_id in rescue_documents:
            return StageOutcomeV1.GRAPH_RESCUE_REQUIRED
        return StageOutcomeV1.GRAPH_RESOLVED
    if stage is FormalStageV1.GEMMA_RESCUE:
        return StageOutcomeV1.GEMMA_RESOLVED
    if stage is FormalStageV1.NUMERIC_PIXEL:
        return StageOutcomeV1.NUMERIC_VERIFIED
    if stage is FormalStageV1.MAPPING:
        return StageOutcomeV1.MAPPING_RESOLVED
    return StageOutcomeV1.SEALED


def _coverage(
    stage: FormalStageV1,
    outcome: StageOutcomeV1,
    document: CurrentDocumentRefsV1,
) -> PageCoverageBoundV1 | None:
    if outcome is StageOutcomeV1.RETRIEVAL_HIT:
        return PageCoverageBoundV1(
            CoverageKindV1.BOUNDED_POSITIVE_SHORTLIST,
            document.page_set_ref,
            document.page_count,
            2,
        )
    if outcome is StageOutcomeV1.RETRIEVAL_ZERO_HIT:
        return PageCoverageBoundV1(
            CoverageKindV1.ZERO_HIT_FULL_DOCUMENT_FALLBACK,
            document.page_set_ref,
            document.page_count,
            document.page_count,
        )
    if outcome is StageOutcomeV1.GRAPH_NOT_OBSERVED:
        return PageCoverageBoundV1(
            CoverageKindV1.COMPLETE_DOCUMENT_NEGATIVE,
            document.page_set_ref,
            document.page_count,
            document.page_count,
        )
    return None


def _complete_cache(
    documents: tuple[CurrentDocumentRefsV1, ...],
    pins: dict[FormalStageV1, StagePinsV1],
    *,
    rescue_documents: frozenset[str] = frozenset(),
    absent_documents: frozenset[str] = frozenset(),
    zero_hit_documents: frozenset[str] = frozenset(),
):
    by_id = {item.document_id: item for item in documents}
    receipts = ()
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
        additions = []
        for item in plan.runnable:
            document = by_id[item.document_id]
            outcome = _outcome(
                item.stage,
                item.document_id,
                rescue_documents=rescue_documents,
                absent_documents=absent_documents,
                zero_hit_documents=zero_hit_documents,
            )
            additions.append(
                build_stage_receipt_v1(
                    item,
                    page_count=document.page_count,
                    output_sha256=_digest(f"{item.expected_stage_key}:{outcome.value}"),
                    output_size_bytes=37,
                    outcome=outcome,
                    coverage_bound=_coverage(item.stage, outcome, document),
                )
            )
        receipts = (*receipts, *additions)
    raise AssertionError("synthetic formal DAG did not converge")


_FAMILY_ID = "TEST_ACCOUNTING_FAMILY"


def _attempt(
    planned: PlannedStageV1,
    document: CurrentDocumentRefsV1,
    ordinal: int,
    *,
    kind: AttemptKindV1 = AttemptKindV1.STAGE_FAILURE,
    failure_class: str | None = "TABLE_GEOMETRY_FAILURE",
    reason_code: str | None = "ROW_AXIS_DID_NOT_CLOSE",
    runtime_budget_ms: int | None = None,
    observed_runtime_ms: int | None = None,
) -> StageAttemptObservationV1:
    if kind is AttemptKindV1.RUNTIME_BUDGET_BREACH:
        failure_class = None
        reason_code = None
    return build_stage_attempt_observation_v1(
        planned,
        family_id=_FAMILY_ID,
        page_count=document.page_count,
        attempt_ordinal=ordinal,
        kind=kind,
        failure_class=failure_class,
        reason_code=reason_code,
        runtime_budget_ms=runtime_budget_ms,
        observed_runtime_ms=observed_runtime_ms,
    )


def _dependency_payload(value: DependencyRefV1) -> dict:
    ref = value.content_ref
    return {
        "role": value.role,
        "content_ref": {
            "kind": ref.kind.value,
            "logical_id": ref.logical_id,
            "sha256": ref.sha256,
            "size_bytes": ref.size_bytes,
        },
    }


def _coherently_rehash_attempt(value: StageAttemptObservationV1) -> StageAttemptObservationV1:
    signature = "ffifdv1:failure:" + canonical_json_sha256_v1(
        {
            "format_version": value.format_version,
            "family_id": value.family_id,
            "stage": value.stage.value,
            "algorithm_revision_key": value.algorithm_revision_key,
            "kind": value.kind.value,
            "failure_class": value.failure_class,
            "reason_code": value.reason_code,
        }
    )
    signed = replace(value, failure_signature=signature, observation_id="")
    identity = "ffifdv1:attempt:" + canonical_json_sha256_v1(
        {
            "format_version": signed.format_version,
            "claim_boundary": signed.claim_boundary,
            "family_id": signed.family_id,
            "document_id": signed.document_id,
            "page_count": signed.page_count,
            "stage": signed.stage.value,
            "dependencies": [_dependency_payload(item) for item in signed.dependencies],
            "algorithm_revision_key": signed.algorithm_revision_key,
            "stage_key": signed.stage_key,
            "attempt_ordinal": signed.attempt_ordinal,
            "kind": signed.kind.value,
            "failure_class": signed.failure_class,
            "reason_code": signed.reason_code,
            "runtime_budget_ms": signed.runtime_budget_ms,
            "observed_runtime_ms": signed.observed_runtime_ms,
            "failure_signature": signed.failure_signature,
        }
    )
    return replace(signed, observation_id=identity)


def _changed_graph_frontier():
    documents = _documents()
    baseline_pins = _pins()
    receipts = _complete_cache(documents, baseline_pins)
    current_pins = _pins(graph_spec="graph-spec-v2")
    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=current_pins,
        cached_receipts=receipts,
        dev_document_ids=(documents[0].document_id,),
        family_id=_FAMILY_ID,
    )
    graph = _decision(plan.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert graph.decision is CacheDecisionV1.RECOMPUTE
    return documents, current_pins, receipts, graph


def _current_graph_frontier(
    documents: tuple[CurrentDocumentRefsV1, ...],
    pins: dict[FormalStageV1, StagePinsV1],
    receipts: tuple[StageReceiptV1, ...],
    document_id: str,
) -> PlannedStageV1:
    retained = tuple(
        item
        for item in receipts
        if item.document_id != document_id
        or item.stage
        in {
            FormalStageV1.SOURCE,
            FormalStageV1.NORMALIZED_SPANS,
            FormalStageV1.RETRIEVAL,
        }
    )
    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=retained,
        dev_document_ids=(document_id,),
        family_id=_FAMILY_ID,
    )
    graph = _decision(plan.decisions, document_id, FormalStageV1.GRAPH)
    assert graph.decision is CacheDecisionV1.RECOMPUTE
    return graph


def test_numeric_only_change_keeps_retrieval_and_graph_hot() -> None:
    documents = _documents()
    receipts = _complete_cache(documents, _pins())

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=_pins(numeric_code="numeric-v2"),
        cached_receipts=receipts,
    )

    document_id = documents[0].document_id
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.RETRIEVAL).decision
        is CacheDecisionV1.HIT
    )
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.GRAPH).decision is CacheDecisionV1.HIT
    )
    assert [(item.document_id, item.stage) for item in plan.runnable] == [
        (document_id, FormalStageV1.NUMERIC_PIXEL)
    ]
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.MAPPING).decision
        is CacheDecisionV1.BLOCKED
    )
    assert stage_invalidation_closure_v1([FormalStageV1.NUMERIC_PIXEL]) == (
        FormalStageV1.NUMERIC_PIXEL,
        FormalStageV1.MAPPING,
        FormalStageV1.SEAL,
    )


def test_alias_spec_change_invalidates_retrieval_downstream_only() -> None:
    documents = _documents()
    receipts = _complete_cache(documents, _pins())

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=_pins(retrieval_spec="aliases-v2"),
        cached_receipts=receipts,
    )

    document_id = documents[0].document_id
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.SOURCE).decision is CacheDecisionV1.HIT
    )
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.NORMALIZED_SPANS).decision
        is CacheDecisionV1.HIT
    )
    assert [(item.document_id, item.stage) for item in plan.runnable] == [
        (document_id, FormalStageV1.RETRIEVAL)
    ]
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.GRAPH).decision
        is CacheDecisionV1.BLOCKED
    )


def test_one_page_root_change_rebuilds_only_its_document() -> None:
    documents = _documents(3)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    changed = replace(
        documents[1],
        document_packet_ref=_ref(ContentRefKindV1.DOCUMENT_PACKET, "packet-002", "v2"),
        page_set_ref=_ref(ContentRefKindV1.PAGE_SET, "pages-002", "one-page-v2"),
    )
    current = (documents[0], changed, documents[2])

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=current,
        stage_pins=pins,
        cached_receipts=receipts,
    )

    assert plan.invalidated_document_ids == ("doc-002",)
    assert [(item.document_id, item.stage) for item in plan.runnable] == [
        ("doc-002", FormalStageV1.SOURCE)
    ]
    for document_id in ("doc-001", "doc-003"):
        assert (
            _decision(plan.decisions, document_id, FormalStageV1.MAPPING).decision
            is CacheDecisionV1.HIT
        )


@pytest.mark.parametrize(
    ("model", "prompt"),
    (("gemma-model-v2", "gemma-prompt-v1"), ("gemma-model-v1", "gemma-prompt-v2")),
)
def test_model_or_prompt_change_recomputes_only_gemma_branch(model: str, prompt: str) -> None:
    documents = _documents()
    rescue = frozenset({documents[0].document_id})
    receipts = _complete_cache(documents, _pins(), rescue_documents=rescue)

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=_pins(gemma_model=model, gemma_prompt=prompt),
        cached_receipts=receipts,
    )

    document_id = documents[0].document_id
    assert [(item.document_id, item.stage) for item in plan.runnable] == [
        (document_id, FormalStageV1.GEMMA_RESCUE)
    ]
    for stage in (
        FormalStageV1.SOURCE,
        FormalStageV1.NORMALIZED_SPANS,
        FormalStageV1.RETRIEVAL,
        FormalStageV1.GRAPH,
        FormalStageV1.NUMERIC_PIXEL,
    ):
        assert _decision(plan.decisions, document_id, stage).decision is CacheDecisionV1.HIT
    assert (
        _decision(plan.decisions, document_id, FormalStageV1.MAPPING).decision
        is CacheDecisionV1.BLOCKED
    )
    assert stage_invalidation_closure_v1([FormalStageV1.GEMMA_RESCUE]) == (
        FormalStageV1.GEMMA_RESCUE,
        FormalStageV1.MAPPING,
        FormalStageV1.SEAL,
    )


def test_coherently_self_hashed_receipt_cannot_override_caller_current_refs() -> None:
    current = _documents()
    fake = (
        replace(
            current[0],
            document_packet_ref=_ref(ContentRefKindV1.DOCUMENT_PACKET, "packet-001", "forged"),
            source_pdf_ref=_ref(ContentRefKindV1.SOURCE_PDF, "pdf-001", "forged"),
            page_set_ref=_ref(ContentRefKindV1.PAGE_SET, "pages-001", "forged"),
        ),
    )
    forged_cache = _complete_cache(fake, _pins())
    forged_source = tuple(item for item in forged_cache if item.stage is FormalStageV1.SOURCE)

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=current,
        stage_pins=_pins(),
        cached_receipts=forged_source,
        dev_document_ids=(current[0].document_id,),
    )

    source = _decision(plan.decisions, current[0].document_id, FormalStageV1.SOURCE)
    assert source.decision is CacheDecisionV1.RECOMPUTE
    assert source.reason_code == "CURRENT_DEPENDENCY_DRIFT"
    assert "current:document_packet" in source.diagnostic
    assert not plan.cache_hits


def test_historical_stage_keys_can_coexist_but_only_current_key_hits() -> None:
    current = _documents()
    pins = _pins()
    current_source = next(
        item for item in _complete_cache(current, pins) if item.stage is FormalStageV1.SOURCE
    )
    historical_documents = (
        replace(
            current[0],
            document_packet_ref=_ref(ContentRefKindV1.DOCUMENT_PACKET, "packet-001", "historical"),
            page_set_ref=_ref(ContentRefKindV1.PAGE_SET, "pages-001", "historical"),
        ),
    )
    historical_source = next(
        item
        for item in _complete_cache(historical_documents, pins)
        if item.stage is FormalStageV1.SOURCE
    )

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=current,
        stage_pins=pins,
        cached_receipts=(historical_source, current_source),
        dev_document_ids=(current[0].document_id,),
    )

    source = _decision(plan.decisions, current[0].document_id, FormalStageV1.SOURCE)
    assert source.decision is CacheDecisionV1.HIT
    assert source.cached_receipt_id == current_source.receipt_id


def test_zero_hit_and_negative_receipts_require_complete_current_page_bound() -> None:
    documents = _documents()
    pins = _pins()
    document = documents[0]
    receipts = _complete_cache(
        documents,
        pins,
        absent_documents=frozenset({document.document_id}),
        zero_hit_documents=frozenset({document.document_id}),
    )
    hot = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
    )
    assert hot.ready
    assert all(item.claim_boundary == RECEIPT_CLAIM_BOUNDARY for item in receipts)
    assert "NON_AUTHORITATIVE_WITHOUT_CALLER_CURRENT_REFS" in RECEIPT_CLAIM_BOUNDARY

    partial_receipts = tuple(
        item
        for item in receipts
        if item.stage in {FormalStageV1.SOURCE, FormalStageV1.NORMALIZED_SPANS}
    )
    partial = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=partial_receipts,
        dev_document_ids=(document.document_id,),
    )
    retrieval = _decision(partial.decisions, document.document_id, FormalStageV1.RETRIEVAL)
    with pytest.raises(IncrementalFormalDagV1Error, match="complete-document coverage"):
        build_stage_receipt_v1(
            retrieval,
            page_count=document.page_count,
            output_sha256=_digest("bad-zero-hit"),
            output_size_bytes=1,
            outcome=StageOutcomeV1.RETRIEVAL_ZERO_HIT,
            coverage_bound=PageCoverageBoundV1(
                CoverageKindV1.ZERO_HIT_FULL_DOCUMENT_FALLBACK,
                document.page_set_ref,
                document.page_count,
                document.page_count - 1,
            ),
        )

    through_retrieval = tuple(
        item
        for item in receipts
        if item.stage
        in {
            FormalStageV1.SOURCE,
            FormalStageV1.NORMALIZED_SPANS,
            FormalStageV1.RETRIEVAL,
        }
    )
    graph_plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=through_retrieval,
        dev_document_ids=(document.document_id,),
    )
    graph = _decision(graph_plan.decisions, document.document_id, FormalStageV1.GRAPH)
    with pytest.raises(IncrementalFormalDagV1Error, match="complete-document coverage"):
        build_stage_receipt_v1(
            graph,
            page_count=document.page_count,
            output_sha256=_digest("bad-negative"),
            output_size_bytes=1,
            outcome=StageOutcomeV1.GRAPH_NOT_OBSERVED,
            coverage_bound=PageCoverageBoundV1(
                CoverageKindV1.COMPLETE_DOCUMENT_NEGATIVE,
                document.page_set_ref,
                document.page_count,
                document.page_count - 1,
            ),
        )

    foreign_page_set = _ref(ContentRefKindV1.PAGE_SET, "pages-001", "foreign-but-coherent")
    forged_zero = build_stage_receipt_v1(
        retrieval,
        page_count=document.page_count,
        output_sha256=_digest("coherent-zero-hit"),
        output_size_bytes=1,
        outcome=StageOutcomeV1.RETRIEVAL_ZERO_HIT,
        coverage_bound=PageCoverageBoundV1(
            CoverageKindV1.ZERO_HIT_FULL_DOCUMENT_FALLBACK,
            foreign_page_set,
            document.page_count,
            document.page_count,
        ),
    )
    rejected = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=(*partial_receipts, forged_zero),
        dev_document_ids=(document.document_id,),
    )
    decision = _decision(rejected.decisions, document.document_id, FormalStageV1.RETRIEVAL)
    assert decision.decision is CacheDecisionV1.RECOMPUTE
    assert decision.reason_code == "CURRENT_COVERAGE_BOUND_DRIFT"


def test_modes_separate_debug_incremental_and_release_authority() -> None:
    documents = _documents(2)
    pins = _pins()
    receipts = _complete_cache(documents, pins)

    dev = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        dev_document_ids=("doc-002",),
    )
    assert dev.selected_document_ids == ("doc-002",)
    assert {item.document_id for item in dev.decisions} == {"doc-002"}
    assert (
        _decision(dev.decisions, "doc-002", FormalStageV1.SEAL).decision is CacheDecisionV1.SKIPPED
    )
    assert dev.ready

    corpus = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
    )
    assert corpus.selected_document_ids == ("doc-001", "doc-002")
    assert all(
        _decision(corpus.decisions, document.document_id, FormalStageV1.SEAL).decision
        is CacheDecisionV1.SKIPPED
        for document in documents
    )
    assert corpus.ready

    release = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
    )
    assert release.ready
    assert len(release.cache_hits) == 14

    missing_one_seal = tuple(
        item
        for item in receipts
        if not (item.document_id == "doc-002" and item.stage is FormalStageV1.SEAL)
    )
    incomplete_release = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=missing_one_seal,
    )
    assert not incomplete_release.ready
    assert [(item.document_id, item.stage) for item in incomplete_release.runnable] == [
        ("doc-002", FormalStageV1.SEAL)
    ]


def test_malformed_or_duplicate_receipts_fail_fast() -> None:
    documents = _documents()
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    source = next(item for item in receipts if item.stage is FormalStageV1.SOURCE)
    malformed = replace(source, receipt_id="ffifdv1:receipt:" + "0" * 64)

    with pytest.raises(IncrementalFormalDagV1Error, match="receipt self-hash"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.CORPUS_INCREMENTAL,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=(malformed,),
        )
    with pytest.raises(IncrementalFormalDagV1Error, match="repeat"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.CORPUS_INCREMENTAL,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=(source, source),
        )


def test_synthetic_140_document_hot_plan_and_one_document_delta() -> None:
    documents = _documents(140)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    hot = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
    )
    assert hot.ready
    assert len(hot.cache_hits) == 6 * 140
    assert not hot.runnable

    changed_document = replace(
        documents[84],
        document_packet_ref=_ref(ContentRefKindV1.DOCUMENT_PACKET, "packet-085", "v2"),
        page_set_ref=_ref(ContentRefKindV1.PAGE_SET, "pages-085", "one-page-v2"),
    )
    changed_documents = (*documents[:84], changed_document, *documents[85:])
    delta = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=changed_documents,
        stage_pins=pins,
        cached_receipts=receipts,
    )
    assert delta.invalidated_document_ids == ("doc-085",)
    assert [(item.document_id, item.stage) for item in delta.runnable] == [
        ("doc-085", FormalStageV1.SOURCE)
    ]
    assert len(delta.cache_hits) == 6 * 139


def test_first_failure_forces_targeted_recompute_and_second_signature_blocks() -> None:
    documents, pins, receipts, graph = _changed_graph_frontier()
    first = _attempt(graph, documents[0], 1)

    first_plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=(first,),
    )
    first_graph = _decision(first_plan.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert first_graph.decision is CacheDecisionV1.RECOMPUTE
    assert first_graph.reason_code == "TARGETED_RECOMPUTE_AFTER_STAGE_FAILURE"
    assert [(item.document_id, item.stage) for item in first_plan.runnable] == [
        (documents[0].document_id, FormalStageV1.GRAPH)
    ]

    second = _attempt(first_graph, documents[0], 2)
    blocked = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=(first, second),
    )
    blocked_graph = _decision(blocked.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert blocked_graph.decision is CacheDecisionV1.BLOCKED
    assert blocked_graph.reason_code == "ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE"
    assert not blocked.runnable


def test_same_generic_failure_across_documents_blocks_the_algorithm_revision() -> None:
    documents = _documents(2)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    graph_a = _current_graph_frontier(documents, pins, receipts, "doc-001")
    graph_b = _current_graph_frontier(documents, pins, receipts, "doc-002")
    failure_a = _attempt(graph_a, documents[0], 1)
    failure_b = _attempt(graph_b, documents[1], 1)

    assert failure_a.stage_key != failure_b.stage_key
    assert failure_a.algorithm_revision_key == failure_b.algorithm_revision_key
    assert failure_a.failure_signature == failure_b.failure_signature

    blocked = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=(failure_a, failure_b),
    )

    for document in documents:
        graph = _decision(blocked.decisions, document.document_id, FormalStageV1.GRAPH)
        assert graph.decision is CacheDecisionV1.BLOCKED
        assert graph.reason_code == "ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE"
    assert not blocked.runnable


def test_third_failure_cannot_bypass_review_by_changing_failure_codes() -> None:
    documents, pins, receipts, graph = _changed_graph_frontier()
    attempts = tuple(
        _attempt(
            graph,
            documents[0],
            ordinal,
            failure_class=f"TABLE_GEOMETRY_FAILURE_{ordinal}",
            reason_code=f"DIFFERENT_METADATA_{ordinal}",
        )
        for ordinal in range(1, 4)
    )

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        dev_document_ids=(documents[0].document_id,),
        family_id=_FAMILY_ID,
        attempt_history=attempts,
    )

    decision = _decision(plan.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert decision.decision is CacheDecisionV1.BLOCKED
    assert decision.reason_code == "ALGORITHM_REVIEW_REQUIRED_FAILURE_ATTEMPT_LIMIT"


def test_stage_key_revision_unblocks_only_targeted_recompute_not_cache_hit() -> None:
    documents, pins_v2, receipts, graph = _changed_graph_frontier()
    attempts = (_attempt(graph, documents[0], 1), _attempt(graph, documents[0], 2))
    pins_v3 = _pins(graph_spec="graph-spec-v3")

    revised_frontier = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins_v3,
        cached_receipts=receipts,
        dev_document_ids=(documents[0].document_id,),
        family_id=_FAMILY_ID,
        attempt_history=attempts,
    )
    revised_graph = _decision(
        revised_frontier.decisions, documents[0].document_id, FormalStageV1.GRAPH
    )
    exact_revised_receipt = build_stage_receipt_v1(
        revised_graph,
        page_count=documents[0].page_count,
        output_sha256=_digest("revised-graph-output"),
        output_size_bytes=37,
        outcome=StageOutcomeV1.GRAPH_RESOLVED,
    )
    revised = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins_v3,
        cached_receipts=(*receipts, exact_revised_receipt),
        dev_document_ids=(documents[0].document_id,),
        family_id=_FAMILY_ID,
        attempt_history=attempts,
    )

    decision = _decision(revised.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert pins_v2 != pins_v3
    assert decision.expected_stage_key != graph.expected_stage_key
    assert decision.decision is CacheDecisionV1.RECOMPUTE
    assert decision.reason_code == "TARGETED_RECOMPUTE_AFTER_STAGE_KEY_REVISION"
    assert decision.cached_receipt_id == exact_revised_receipt.receipt_id
    assert decision not in revised.cache_hits


def test_one_runtime_budget_breach_recomputes_and_two_block() -> None:
    documents = _documents(2)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    graph = _current_graph_frontier(documents, pins, receipts, "doc-001")
    first = _attempt(
        graph,
        documents[0],
        1,
        kind=AttemptKindV1.RUNTIME_BUDGET_BREACH,
        runtime_budget_ms=1_000,
        observed_runtime_ms=1_001,
    )
    once = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        dev_document_ids=("doc-001",),
        family_id=_FAMILY_ID,
        attempt_history=(first,),
    )
    once_graph = _decision(once.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    assert once_graph.decision is CacheDecisionV1.RECOMPUTE
    assert once_graph.reason_code == "TARGETED_RECOMPUTE_AFTER_RUNTIME_BUDGET_BREACH"

    graph_b = _current_graph_frontier(documents, pins, receipts, "doc-002")
    second = _attempt(
        graph_b,
        documents[1],
        1,
        kind=AttemptKindV1.RUNTIME_BUDGET_BREACH,
        runtime_budget_ms=1_000,
        observed_runtime_ms=1_250,
    )
    twice = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=(first, second),
    )
    for document in documents:
        twice_graph = _decision(twice.decisions, document.document_id, FormalStageV1.GRAPH)
        assert twice_graph.decision is CacheDecisionV1.BLOCKED
        assert twice_graph.reason_code == "ALGORITHM_REVIEW_REQUIRED_RUNTIME_BUDGET"


def test_attempt_history_changes_only_its_exact_document_stage_key() -> None:
    documents = _documents(2)
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    graph = _current_graph_frontier(documents, pins, receipts, "doc-001")
    first = _attempt(graph, documents[0], 1)

    plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.CORPUS_INCREMENTAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=(first,),
    )

    assert _decision(plan.decisions, "doc-001", FormalStageV1.SOURCE).decision is (
        CacheDecisionV1.HIT
    )
    assert _decision(plan.decisions, "doc-001", FormalStageV1.GRAPH).decision is (
        CacheDecisionV1.RECOMPUTE
    )
    for stage in (
        FormalStageV1.SOURCE,
        FormalStageV1.NORMALIZED_SPANS,
        FormalStageV1.RETRIEVAL,
        FormalStageV1.GRAPH,
        FormalStageV1.NUMERIC_PIXEL,
        FormalStageV1.MAPPING,
    ):
        assert _decision(plan.decisions, "doc-002", stage).decision is CacheDecisionV1.HIT


def test_attempt_history_exact_types_identity_family_and_document_fail_closed() -> None:
    documents, pins, receipts, graph = _changed_graph_frontier()
    attempt = _attempt(graph, documents[0], 1)
    assert attempt.claim_boundary == ATTEMPT_CLAIM_BOUNDARY

    malformed = (
        replace(attempt, attempt_ordinal=True),
        replace(attempt, page_count=True),
        replace(attempt, observation_id="ffifdv1:attempt:" + "0" * 64),
        replace(attempt, failure_signature="ffifdv1:failure:" + "0" * 64),
        replace(attempt, stage="UNKNOWN"),
    )
    for item in malformed:
        with pytest.raises(IncrementalFormalDagV1Error):
            plan_incremental_formal_dag_v1(
                mode=PlanModeV1.DEV_FAST,
                current_documents=documents,
                stage_pins=pins,
                cached_receipts=receipts,
                dev_document_ids=(documents[0].document_id,),
                family_id=_FAMILY_ID,
                attempt_history=(item,),
            )
    with pytest.raises(IncrementalFormalDagV1Error, match="exact tuple"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.DEV_FAST,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
            dev_document_ids=(documents[0].document_id,),
            family_id=_FAMILY_ID,
            attempt_history=[attempt],
        )
    with pytest.raises(IncrementalFormalDagV1Error, match="repeats"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.DEV_FAST,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
            dev_document_ids=(documents[0].document_id,),
            family_id=_FAMILY_ID,
            attempt_history=(attempt, attempt),
        )
    with pytest.raises(IncrementalFormalDagV1Error, match="runtime-budget"):
        build_stage_attempt_observation_v1(
            graph,
            family_id=_FAMILY_ID,
            page_count=documents[0].page_count,
            attempt_ordinal=1,
            kind=AttemptKindV1.RUNTIME_BUDGET_BREACH,
            runtime_budget_ms=True,
            observed_runtime_ms=2,
        )

    forged_family = _coherently_rehash_attempt(replace(attempt, family_id="DIFFERENT_FAMILY"))
    with pytest.raises(IncrementalFormalDagV1Error, match="caller-current family"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.DEV_FAST,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
            dev_document_ids=(documents[0].document_id,),
            family_id=_FAMILY_ID,
            attempt_history=(forged_family,),
        )

    foreign_documents = _documents(2)
    foreign_plan = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.DEV_FAST,
        current_documents=foreign_documents,
        stage_pins=_pins(),
        dev_document_ids=("doc-002",),
        family_id=_FAMILY_ID,
    )
    foreign_source = _decision(foreign_plan.decisions, "doc-002", FormalStageV1.SOURCE)
    foreign_attempt = _attempt(foreign_source, foreign_documents[1], 1)
    with pytest.raises(IncrementalFormalDagV1Error, match="unknown document"):
        plan_incremental_formal_dag_v1(
            mode=PlanModeV1.DEV_FAST,
            current_documents=documents,
            stage_pins=pins,
            cached_receipts=receipts,
            dev_document_ids=(documents[0].document_id,),
            family_id=_FAMILY_ID,
            attempt_history=(foreign_attempt,),
        )


def test_release_seal_propagates_algorithm_review_block() -> None:
    documents = _documents()
    pins = _pins()
    receipts = _complete_cache(documents, pins)
    graph = _current_graph_frontier(documents, pins, receipts, documents[0].document_id)
    attempts = (_attempt(graph, documents[0], 1), _attempt(graph, documents[0], 2))

    release = plan_incremental_formal_dag_v1(
        mode=PlanModeV1.RELEASE_SEAL,
        current_documents=documents,
        stage_pins=pins,
        cached_receipts=receipts,
        family_id=_FAMILY_ID,
        attempt_history=attempts,
    )

    graph_decision = _decision(release.decisions, documents[0].document_id, FormalStageV1.GRAPH)
    seal_decision = _decision(release.decisions, documents[0].document_id, FormalStageV1.SEAL)
    assert graph_decision.reason_code == "ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE"
    assert seal_decision.decision is CacheDecisionV1.BLOCKED
    assert seal_decision.reason_code == "ALGORITHM_REVIEW_REQUIRED_UPSTREAM_BLOCKED"
    assert not release.ready
    assert seal_decision not in release.cache_hits
