"""Pure, new-only planner for family-first formal evidence stages.

The planner deliberately does not authenticate files, execute algorithms, or
write a cache.  Its caller must project ``CurrentDocumentRefsV1`` from the live
authenticated document store and must authenticate cached output bytes before
passing their receipts here.  Given those inputs, this module answers one
question: which content-addressed stage outputs can be reused exactly, and
which smallest frontier must run next?

A receipt's internally coherent hashes are never sufficient for a hit.  Every
stage key is independently rebuilt from caller-current document refs, exact
typed code/spec/model/prompt pins, and already accepted upstream outputs.
Zero-hit retrieval and complete-document negative graph outcomes additionally
bind the exact current page-set root and page denominator.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

__all__ = [
    "FORMAT_VERSION",
    "RECEIPT_CLAIM_BOUNDARY",
    "CacheDecisionV1",
    "ContentRefKindV1",
    "CoverageKindV1",
    "CurrentDocumentRefsV1",
    "DependencyRefV1",
    "FormalStageV1",
    "IncrementalFormalDagV1Error",
    "IncrementalFormalPlanV1",
    "PageCoverageBoundV1",
    "PlanModeV1",
    "PlannedStageV1",
    "StageOutcomeV1",
    "StagePinsV1",
    "StageReceiptV1",
    "TypedContentRefV1",
    "build_stage_receipt_v1",
    "plan_incremental_formal_dag_v1",
    "stage_invalidation_closure_v1",
]


FORMAT_VERSION = "FAMILY_FIRST_INCREMENTAL_FORMAL_DAG_V1"
_RECEIPT_FORMAT_VERSION = "FAMILY_FIRST_INCREMENTAL_FORMAL_STAGE_RECEIPT_V1"
RECEIPT_CLAIM_BOUNDARY = (
    "CONTENT_BOOKKEEPING_ONLY_NON_AUTHORITATIVE_WITHOUT_CALLER_CURRENT_REFS_"
    "FROM_A_LIVE_AUTHENTICATED_STORE_AND_SEPARATELY_AUTHENTICATED_OUTPUT_BYTES"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class IncrementalFormalDagV1Error(ValueError):
    """The current-ref set, pins, receipt, or DAG request is malformed."""


class FormalStageV1(StrEnum):
    SOURCE = "SOURCE"
    NORMALIZED_SPANS = "NORMALIZED_SPANS"
    RETRIEVAL = "RETRIEVAL"
    GRAPH = "GRAPH"
    GEMMA_RESCUE = "GEMMA_RESCUE"
    NUMERIC_PIXEL = "NUMERIC_PIXEL"
    MAPPING = "MAPPING"
    SEAL = "SEAL"


class PlanModeV1(StrEnum):
    DEV_FAST = "DEV_FAST"
    CORPUS_INCREMENTAL = "CORPUS_INCREMENTAL"
    RELEASE_SEAL = "RELEASE_SEAL"


class ContentRefKindV1(StrEnum):
    DOCUMENT_PACKET = "DOCUMENT_PACKET"
    SOURCE_PDF = "SOURCE_PDF"
    PAGE_SET = "PAGE_SET"
    CODE = "CODE"
    SPEC = "SPEC"
    MODEL = "MODEL"
    PROMPT = "PROMPT"
    STAGE_OUTPUT = "STAGE_OUTPUT"


class CoverageKindV1(StrEnum):
    BOUNDED_POSITIVE_SHORTLIST = "BOUNDED_POSITIVE_SHORTLIST"
    ZERO_HIT_FULL_DOCUMENT_FALLBACK = "ZERO_HIT_FULL_DOCUMENT_FALLBACK"
    COMPLETE_DOCUMENT_NEGATIVE = "COMPLETE_DOCUMENT_NEGATIVE"


class StageOutcomeV1(StrEnum):
    SOURCE_READY = "SOURCE_READY"
    NORMALIZED_SPANS_READY = "NORMALIZED_SPANS_READY"
    RETRIEVAL_HIT = "RETRIEVAL_HIT"
    RETRIEVAL_ZERO_HIT = "RETRIEVAL_ZERO_HIT"
    GRAPH_RESOLVED = "GRAPH_RESOLVED"
    GRAPH_NOT_OBSERVED = "GRAPH_NOT_OBSERVED"
    GRAPH_RESCUE_REQUIRED = "GRAPH_RESCUE_REQUIRED"
    GEMMA_RESOLVED = "GEMMA_RESOLVED"
    GEMMA_UNRESOLVED = "GEMMA_UNRESOLVED"
    NUMERIC_VERIFIED = "NUMERIC_VERIFIED"
    NUMERIC_UNRESOLVED = "NUMERIC_UNRESOLVED"
    MAPPING_RESOLVED = "MAPPING_RESOLVED"
    MAPPING_UNRESOLVED = "MAPPING_UNRESOLVED"
    SEALED = "SEALED"


class CacheDecisionV1(StrEnum):
    HIT = "HIT"
    RECOMPUTE = "RECOMPUTE"
    BLOCKED = "BLOCKED"
    SKIPPED = "SKIPPED"


_STAGE_ORDER = (
    FormalStageV1.SOURCE,
    FormalStageV1.NORMALIZED_SPANS,
    FormalStageV1.RETRIEVAL,
    FormalStageV1.GRAPH,
    FormalStageV1.GEMMA_RESCUE,
    FormalStageV1.NUMERIC_PIXEL,
    FormalStageV1.MAPPING,
    FormalStageV1.SEAL,
)
_OUTCOMES_BY_STAGE = {
    FormalStageV1.SOURCE: {StageOutcomeV1.SOURCE_READY},
    FormalStageV1.NORMALIZED_SPANS: {StageOutcomeV1.NORMALIZED_SPANS_READY},
    FormalStageV1.RETRIEVAL: {
        StageOutcomeV1.RETRIEVAL_HIT,
        StageOutcomeV1.RETRIEVAL_ZERO_HIT,
    },
    FormalStageV1.GRAPH: {
        StageOutcomeV1.GRAPH_RESOLVED,
        StageOutcomeV1.GRAPH_NOT_OBSERVED,
        StageOutcomeV1.GRAPH_RESCUE_REQUIRED,
    },
    FormalStageV1.GEMMA_RESCUE: {
        StageOutcomeV1.GEMMA_RESOLVED,
        StageOutcomeV1.GEMMA_UNRESOLVED,
    },
    FormalStageV1.NUMERIC_PIXEL: {
        StageOutcomeV1.NUMERIC_VERIFIED,
        StageOutcomeV1.NUMERIC_UNRESOLVED,
    },
    FormalStageV1.MAPPING: {
        StageOutcomeV1.MAPPING_RESOLVED,
        StageOutcomeV1.MAPPING_UNRESOLVED,
    },
    FormalStageV1.SEAL: {StageOutcomeV1.SEALED},
}
_STATIC_CHILDREN = {
    FormalStageV1.SOURCE: {
        FormalStageV1.NORMALIZED_SPANS,
        FormalStageV1.GEMMA_RESCUE,
        FormalStageV1.NUMERIC_PIXEL,
    },
    FormalStageV1.NORMALIZED_SPANS: {
        FormalStageV1.RETRIEVAL,
        FormalStageV1.GRAPH,
        FormalStageV1.GEMMA_RESCUE,
    },
    FormalStageV1.RETRIEVAL: {FormalStageV1.GRAPH, FormalStageV1.GEMMA_RESCUE},
    FormalStageV1.GRAPH: {
        FormalStageV1.GEMMA_RESCUE,
        FormalStageV1.NUMERIC_PIXEL,
        FormalStageV1.MAPPING,
    },
    FormalStageV1.GEMMA_RESCUE: {FormalStageV1.MAPPING},
    FormalStageV1.NUMERIC_PIXEL: {FormalStageV1.MAPPING},
    FormalStageV1.MAPPING: {FormalStageV1.SEAL},
    FormalStageV1.SEAL: set(),
}


def _error(message: str) -> IncrementalFormalDagV1Error:
    return IncrementalFormalDagV1Error(message)


@dataclass(frozen=True, slots=True)
class TypedContentRefV1:
    kind: ContentRefKindV1
    logical_id: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class DependencyRefV1:
    role: str
    content_ref: TypedContentRefV1


@dataclass(frozen=True, slots=True)
class StagePinsV1:
    code_refs: tuple[TypedContentRefV1, ...]
    spec_refs: tuple[TypedContentRefV1, ...] = ()
    model_refs: tuple[TypedContentRefV1, ...] = ()
    prompt_refs: tuple[TypedContentRefV1, ...] = ()


@dataclass(frozen=True, slots=True)
class CurrentDocumentRefsV1:
    document_ordinal: int
    document_id: str
    document_packet_ref: TypedContentRefV1
    source_pdf_ref: TypedContentRefV1
    page_set_ref: TypedContentRefV1
    page_count: int


@dataclass(frozen=True, slots=True)
class PageCoverageBoundV1:
    kind: CoverageKindV1
    page_set_ref: TypedContentRefV1
    page_count: int
    covered_page_count: int


@dataclass(frozen=True, slots=True)
class _ExpectedStageNodeV1:
    document_id: str
    page_count: int
    stage: FormalStageV1
    dependencies: tuple[DependencyRefV1, ...]
    stage_key: str


@dataclass(frozen=True, slots=True)
class StageReceiptV1:
    format_version: str
    claim_boundary: str
    document_id: str
    page_count: int
    stage: FormalStageV1
    dependencies: tuple[DependencyRefV1, ...]
    stage_key: str
    output_ref: TypedContentRefV1
    outcome: StageOutcomeV1
    coverage_bound: PageCoverageBoundV1 | None
    receipt_id: str


@dataclass(frozen=True, slots=True)
class PlannedStageV1:
    document_id: str
    stage: FormalStageV1
    decision: CacheDecisionV1
    reason_code: str
    diagnostic: str
    expected_stage_key: str | None
    expected_dependencies: tuple[DependencyRefV1, ...]
    cached_receipt_id: str | None


@dataclass(frozen=True, slots=True)
class IncrementalFormalPlanV1:
    format_version: str
    mode: PlanModeV1
    current_document_count: int
    selected_document_ids: tuple[str, ...]
    decisions: tuple[PlannedStageV1, ...]
    ready: bool

    @property
    def runnable(self) -> tuple[PlannedStageV1, ...]:
        """The smallest currently executable frontier; cache hits never appear."""

        return tuple(item for item in self.decisions if item.decision is CacheDecisionV1.RECOMPUTE)

    @property
    def cache_hits(self) -> tuple[PlannedStageV1, ...]:
        return tuple(item for item in self.decisions if item.decision is CacheDecisionV1.HIT)

    @property
    def invalidated_document_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    item.document_id
                    for item in self.decisions
                    if item.decision in {CacheDecisionV1.RECOMPUTE, CacheDecisionV1.BLOCKED}
                }
            )
        )


def _ref_payload(value: TypedContentRefV1) -> dict[str, Any]:
    return {
        "kind": value.kind.value,
        "logical_id": value.logical_id,
        "sha256": value.sha256,
        "size_bytes": value.size_bytes,
    }


def _dependency_payload(value: DependencyRefV1) -> dict[str, Any]:
    return {"role": value.role, "content_ref": _ref_payload(value.content_ref)}


def _coverage_payload(value: PageCoverageBoundV1 | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "kind": value.kind.value,
        "page_set_ref": _ref_payload(value.page_set_ref),
        "page_count": value.page_count,
        "covered_page_count": value.covered_page_count,
    }


def _validate_ref(
    value: Any, label: str, expected_kind: ContentRefKindV1 | None = None
) -> TypedContentRefV1:
    if type(value) is not TypedContentRefV1:
        raise _error(f"{label} must be one exact TypedContentRefV1")
    if type(value.kind) is not ContentRefKindV1 or (
        expected_kind is not None and value.kind is not expected_kind
    ):
        raise _error(f"{label} kind drifted")
    if (
        type(value.logical_id) is not str
        or not value.logical_id
        or value.logical_id != value.logical_id.strip()
        or len(value.logical_id) > 512
        or type(value.sha256) is not str
        or _SHA256.fullmatch(value.sha256) is None
        or type(value.size_bytes) is not int
        or value.size_bytes < 0
    ):
        raise _error(f"{label} content identity drifted")
    return value


def _validate_dependency(value: Any, label: str) -> DependencyRefV1:
    if (
        type(value) is not DependencyRefV1
        or type(value.role) is not str
        or not value.role
        or value.role != value.role.strip()
        or len(value.role) > 640
    ):
        raise _error(f"{label} dependency role drifted")
    _validate_ref(value.content_ref, f"{label} content ref")
    return value


def _validate_dependencies(
    value: Any, label: str, *, allow_empty: bool = False
) -> tuple[DependencyRefV1, ...]:
    if type(value) is not tuple or (not value and not allow_empty):
        raise _error(f"{label} must be one nonempty dependency tuple")
    for index, item in enumerate(value):
        _validate_dependency(item, f"{label}[{index}]")
    roles = tuple(item.role for item in value)
    if roles != tuple(sorted(set(roles))):
        raise _error(f"{label} roles must be sorted and unique")
    return value


def _validate_ref_tuple(
    value: Any, label: str, expected_kind: ContentRefKindV1, *, allow_empty: bool
) -> tuple[TypedContentRefV1, ...]:
    if type(value) is not tuple or (not allow_empty and not value):
        raise _error(f"{label} reference tuple drifted")
    for index, item in enumerate(value):
        _validate_ref(item, f"{label}[{index}]", expected_kind)
    order = tuple((item.logical_id, item.sha256, item.size_bytes) for item in value)
    if order != tuple(sorted(set(order))):
        raise _error(f"{label} references must be sorted and unique")
    return value


def _validate_pins(stage: FormalStageV1, value: Any) -> StagePinsV1:
    if type(value) is not StagePinsV1:
        raise _error(f"{stage.value} pins must be one exact StagePinsV1")
    _validate_ref_tuple(
        value.code_refs, f"{stage.value} code", ContentRefKindV1.CODE, allow_empty=False
    )
    _validate_ref_tuple(
        value.spec_refs, f"{stage.value} spec", ContentRefKindV1.SPEC, allow_empty=True
    )
    _validate_ref_tuple(
        value.model_refs, f"{stage.value} model", ContentRefKindV1.MODEL, allow_empty=True
    )
    _validate_ref_tuple(
        value.prompt_refs, f"{stage.value} prompt", ContentRefKindV1.PROMPT, allow_empty=True
    )
    if stage is FormalStageV1.GEMMA_RESCUE:
        if not value.model_refs or not value.prompt_refs:
            raise _error("GEMMA_RESCUE pins require exact model and prompt refs")
    elif value.model_refs or value.prompt_refs:
        raise _error("model/prompt refs are isolated to GEMMA_RESCUE")
    if (
        stage
        in {
            FormalStageV1.RETRIEVAL,
            FormalStageV1.GRAPH,
            FormalStageV1.NUMERIC_PIXEL,
            FormalStageV1.MAPPING,
            FormalStageV1.SEAL,
        }
        and not value.spec_refs
    ):
        raise _error(f"{stage.value} pins require at least one exact spec ref")
    return value


def _validate_document(value: Any) -> CurrentDocumentRefsV1:
    if type(value) is not CurrentDocumentRefsV1:
        raise _error("current document must be one exact CurrentDocumentRefsV1")
    if (
        type(value.document_ordinal) is not int
        or value.document_ordinal <= 0
        or type(value.document_id) is not str
        or not value.document_id
        or value.document_id != value.document_id.strip()
        or type(value.page_count) is not int
        or value.page_count <= 0
    ):
        raise _error("current document identity/denominator drifted")
    _validate_ref(value.document_packet_ref, "document packet", ContentRefKindV1.DOCUMENT_PACKET)
    _validate_ref(value.source_pdf_ref, "source PDF", ContentRefKindV1.SOURCE_PDF)
    _validate_ref(value.page_set_ref, "page set", ContentRefKindV1.PAGE_SET)
    return value


def _stage_key(
    document_id: str,
    page_count: int,
    stage: FormalStageV1,
    dependencies: tuple[DependencyRefV1, ...],
) -> str:
    material = {
        "format_version": FORMAT_VERSION,
        "document_id": document_id,
        "page_count": page_count,
        "stage": stage.value,
        "dependencies": [_dependency_payload(item) for item in dependencies],
    }
    return f"ffifdv1:stage:{canonical_json_sha256_v1(material)}"


def _receipt_id(value: StageReceiptV1) -> str:
    material = {
        "format_version": value.format_version,
        "claim_boundary": value.claim_boundary,
        "document_id": value.document_id,
        "page_count": value.page_count,
        "stage": value.stage.value,
        "dependencies": [_dependency_payload(item) for item in value.dependencies],
        "stage_key": value.stage_key,
        "output_ref": _ref_payload(value.output_ref),
        "outcome": value.outcome.value,
        "coverage_bound": _coverage_payload(value.coverage_bound),
    }
    return f"ffifdv1:receipt:{canonical_json_sha256_v1(material)}"


def _expected_output_logical_id(document_id: str, stage: FormalStageV1) -> str:
    return f"ffifdv1/output/{document_id}/{stage.value.lower()}"


def _validate_coverage_shape(
    coverage: Any, *, stage: FormalStageV1, outcome: StageOutcomeV1, page_count: int
) -> None:
    required: CoverageKindV1 | None = None
    if outcome is StageOutcomeV1.RETRIEVAL_HIT:
        required = CoverageKindV1.BOUNDED_POSITIVE_SHORTLIST
    elif outcome is StageOutcomeV1.RETRIEVAL_ZERO_HIT:
        required = CoverageKindV1.ZERO_HIT_FULL_DOCUMENT_FALLBACK
    elif outcome is StageOutcomeV1.GRAPH_NOT_OBSERVED:
        required = CoverageKindV1.COMPLETE_DOCUMENT_NEGATIVE
    if required is None:
        if coverage is not None:
            raise _error(f"{stage.value}/{outcome.value} must not carry a coverage bound")
        return
    if type(coverage) is not PageCoverageBoundV1 or coverage.kind is not required:
        raise _error(f"{stage.value}/{outcome.value} coverage kind drifted")
    _validate_ref(coverage.page_set_ref, "coverage page set", ContentRefKindV1.PAGE_SET)
    if (
        type(coverage.page_count) is not int
        or coverage.page_count != page_count
        or type(coverage.covered_page_count) is not int
        or not 1 <= coverage.covered_page_count <= page_count
    ):
        raise _error(f"{stage.value}/{outcome.value} coverage denominator drifted")
    if (
        required
        in {
            CoverageKindV1.ZERO_HIT_FULL_DOCUMENT_FALLBACK,
            CoverageKindV1.COMPLETE_DOCUMENT_NEGATIVE,
        }
        and coverage.covered_page_count != page_count
    ):
        raise _error(f"{stage.value}/{outcome.value} requires complete-document coverage")


def _validate_receipt(value: Any) -> StageReceiptV1:
    if type(value) is not StageReceiptV1:
        raise _error("cached receipt must be one exact StageReceiptV1")
    if (
        value.format_version != _RECEIPT_FORMAT_VERSION
        or value.claim_boundary != RECEIPT_CLAIM_BOUNDARY
        or type(value.document_id) is not str
        or not value.document_id
        or type(value.page_count) is not int
        or value.page_count <= 0
        or type(value.stage) is not FormalStageV1
        or type(value.outcome) is not StageOutcomeV1
        or value.outcome not in _OUTCOMES_BY_STAGE[value.stage]
    ):
        raise _error("cached receipt identity/outcome drifted")
    _validate_dependencies(value.dependencies, "cached receipt dependencies")
    if value.stage_key != _stage_key(
        value.document_id, value.page_count, value.stage, value.dependencies
    ):
        raise _error("cached receipt stage self-hash drifted")
    _validate_ref(value.output_ref, "cached output", ContentRefKindV1.STAGE_OUTPUT)
    if value.output_ref.logical_id != _expected_output_logical_id(value.document_id, value.stage):
        raise _error("cached output logical identity drifted")
    _validate_coverage_shape(
        value.coverage_bound,
        stage=value.stage,
        outcome=value.outcome,
        page_count=value.page_count,
    )
    if value.receipt_id != _receipt_id(value):
        raise _error("cached receipt self-hash drifted")
    return value


def build_stage_receipt_v1(
    expected_stage: PlannedStageV1,
    *,
    page_count: int,
    output_sha256: str,
    output_size_bytes: int,
    outcome: StageOutcomeV1,
    coverage_bound: PageCoverageBoundV1 | None = None,
) -> StageReceiptV1:
    """Build a serializable receipt after a runner produced one planned output.

    This is content bookkeeping, not authentication and not a cache write.
    Only a currently runnable stage may be recorded, preventing callers from
    inventing downstream dependencies before upstream outputs exist.
    """

    if (
        type(expected_stage) is not PlannedStageV1
        or expected_stage.decision is not CacheDecisionV1.RECOMPUTE
    ):
        raise _error("a receipt can only be built for one runnable planned stage")
    if expected_stage.expected_stage_key is None:
        raise _error("runnable planned stage lacks its independently computed key")
    if type(page_count) is not int or page_count <= 0:
        raise _error("receipt page denominator drifted")
    output_ref = TypedContentRefV1(
        ContentRefKindV1.STAGE_OUTPUT,
        _expected_output_logical_id(expected_stage.document_id, expected_stage.stage),
        output_sha256,
        output_size_bytes,
    )
    _validate_ref(output_ref, "new stage output", ContentRefKindV1.STAGE_OUTPUT)
    if (
        type(outcome) is not StageOutcomeV1
        or outcome not in _OUTCOMES_BY_STAGE[expected_stage.stage]
    ):
        raise _error("new stage outcome does not belong to the planned stage")
    _validate_coverage_shape(
        coverage_bound,
        stage=expected_stage.stage,
        outcome=outcome,
        page_count=page_count,
    )
    provisional = StageReceiptV1(
        _RECEIPT_FORMAT_VERSION,
        RECEIPT_CLAIM_BOUNDARY,
        expected_stage.document_id,
        page_count,
        expected_stage.stage,
        expected_stage.expected_dependencies,
        expected_stage.expected_stage_key,
        output_ref,
        outcome,
        coverage_bound,
        "",
    )
    result = StageReceiptV1(
        provisional.format_version,
        provisional.claim_boundary,
        provisional.document_id,
        provisional.page_count,
        provisional.stage,
        provisional.dependencies,
        provisional.stage_key,
        provisional.output_ref,
        provisional.outcome,
        provisional.coverage_bound,
        _receipt_id(provisional),
    )
    return _validate_receipt(result)


def _pin_dependencies(stage: FormalStageV1, pins: StagePinsV1) -> list[DependencyRefV1]:
    result: list[DependencyRefV1] = []
    for category, refs in (
        ("code", pins.code_refs),
        ("spec", pins.spec_refs),
        ("model", pins.model_refs),
        ("prompt", pins.prompt_refs),
    ):
        result.extend(DependencyRefV1(f"pin:{category}:{item.logical_id}", item) for item in refs)
    if len({item.role for item in result}) != len(result):
        raise _error(f"{stage.value} pin logical IDs collide within one dependency category")
    return result


def _parents_for_stage(
    stage: FormalStageV1,
    graph_outcome: StageOutcomeV1 | None,
) -> tuple[FormalStageV1, ...]:
    if stage is FormalStageV1.SOURCE:
        return ()
    if stage is FormalStageV1.NORMALIZED_SPANS:
        return (FormalStageV1.SOURCE,)
    if stage is FormalStageV1.RETRIEVAL:
        return (FormalStageV1.NORMALIZED_SPANS,)
    if stage is FormalStageV1.GRAPH:
        return (FormalStageV1.NORMALIZED_SPANS, FormalStageV1.RETRIEVAL)
    if stage is FormalStageV1.GEMMA_RESCUE:
        return (
            FormalStageV1.SOURCE,
            FormalStageV1.NORMALIZED_SPANS,
            FormalStageV1.RETRIEVAL,
            FormalStageV1.GRAPH,
        )
    if stage is FormalStageV1.NUMERIC_PIXEL:
        return (FormalStageV1.SOURCE, FormalStageV1.GRAPH)
    if stage is FormalStageV1.MAPPING:
        if graph_outcome is StageOutcomeV1.GRAPH_NOT_OBSERVED:
            return (FormalStageV1.GRAPH,)
        if graph_outcome is StageOutcomeV1.GRAPH_RESCUE_REQUIRED:
            return (
                FormalStageV1.GRAPH,
                FormalStageV1.GEMMA_RESCUE,
                FormalStageV1.NUMERIC_PIXEL,
            )
        return (FormalStageV1.GRAPH, FormalStageV1.NUMERIC_PIXEL)
    return (FormalStageV1.MAPPING,)


def _expected_node(
    document: CurrentDocumentRefsV1,
    stage: FormalStageV1,
    pins: StagePinsV1,
    accepted: Mapping[FormalStageV1, StageReceiptV1],
    graph_outcome: StageOutcomeV1 | None,
) -> _ExpectedStageNodeV1:
    dependencies = _pin_dependencies(stage, pins)
    if stage is FormalStageV1.SOURCE:
        dependencies.extend(
            (
                DependencyRefV1("current:document_packet", document.document_packet_ref),
                DependencyRefV1("current:page_set", document.page_set_ref),
                DependencyRefV1("current:source_pdf", document.source_pdf_ref),
            )
        )
    for parent in _parents_for_stage(stage, graph_outcome):
        dependencies.append(
            DependencyRefV1(f"upstream:{parent.value}", accepted[parent].output_ref)
        )
    ordered = tuple(sorted(dependencies, key=lambda item: item.role))
    _validate_dependencies(ordered, f"{stage.value} expected dependencies")
    return _ExpectedStageNodeV1(
        document.document_id,
        document.page_count,
        stage,
        ordered,
        _stage_key(document.document_id, document.page_count, stage, ordered),
    )


def _mismatched_roles(
    expected: tuple[DependencyRefV1, ...], cached: tuple[DependencyRefV1, ...]
) -> tuple[str, ...]:
    expected_by_role = {item.role: item.content_ref for item in expected}
    cached_by_role = {item.role: item.content_ref for item in cached}
    return tuple(
        role
        for role in sorted(set(expected_by_role) | set(cached_by_role))
        if expected_by_role.get(role) != cached_by_role.get(role)
    )


def _candidate_decision(
    node: _ExpectedStageNodeV1,
    document: CurrentDocumentRefsV1,
    candidates: tuple[StageReceiptV1, ...],
) -> tuple[PlannedStageV1, StageReceiptV1 | None]:
    if not candidates:
        return (
            PlannedStageV1(
                node.document_id,
                node.stage,
                CacheDecisionV1.RECOMPUTE,
                "CACHE_ENTRY_MISSING",
                "no cached receipt exists for the independently computed stage key",
                node.stage_key,
                node.dependencies,
                None,
            ),
            None,
        )
    exact = tuple(item for item in candidates if item.stage_key == node.stage_key)
    if exact:
        candidate = exact[0]
    else:
        # Historical content-addressed variants may coexist. Pick one only to
        # make the miss diagnostic deterministic; it can never become a hit.
        candidate = min(
            candidates,
            key=lambda item: (
                len(_mismatched_roles(node.dependencies, item.dependencies))
                + (item.page_count != node.page_count),
                item.receipt_id,
            ),
        )
    mismatches = _mismatched_roles(node.dependencies, candidate.dependencies)
    if candidate.page_count != node.page_count:
        mismatches = tuple(sorted((*mismatches, "current:page_count")))
    if mismatches or candidate.stage_key != node.stage_key:
        detail = ", ".join(mismatches) if mismatches else "stage-key material"
        return (
            PlannedStageV1(
                node.document_id,
                node.stage,
                CacheDecisionV1.RECOMPUTE,
                "CURRENT_DEPENDENCY_DRIFT",
                f"cached receipt differs from caller-current refs at: {detail}",
                node.stage_key,
                node.dependencies,
                candidate.receipt_id,
            ),
            None,
        )
    coverage = candidate.coverage_bound
    if coverage is not None and coverage.page_set_ref != document.page_set_ref:
        return (
            PlannedStageV1(
                node.document_id,
                node.stage,
                CacheDecisionV1.RECOMPUTE,
                "CURRENT_COVERAGE_BOUND_DRIFT",
                "cached zero-hit/negative coverage does not bind the current page-set root",
                node.stage_key,
                node.dependencies,
                candidate.receipt_id,
            ),
            None,
        )
    return (
        PlannedStageV1(
            node.document_id,
            node.stage,
            CacheDecisionV1.HIT,
            "EXACT_CURRENT_REFS_CACHE_HIT",
            "receipt, current refs, pins, upstream refs, and coverage bind exactly",
            node.stage_key,
            node.dependencies,
            candidate.receipt_id,
        ),
        candidate,
    )


def _skipped(
    document_id: str, stage: FormalStageV1, reason: str, diagnostic: str
) -> PlannedStageV1:
    return PlannedStageV1(
        document_id,
        stage,
        CacheDecisionV1.SKIPPED,
        reason,
        diagnostic,
        None,
        (),
        None,
    )


def _blocked(
    document_id: str, stage: FormalStageV1, reason: str, diagnostic: str
) -> PlannedStageV1:
    return PlannedStageV1(
        document_id,
        stage,
        CacheDecisionV1.BLOCKED,
        reason,
        diagnostic,
        None,
        (),
        None,
    )


def plan_incremental_formal_dag_v1(
    *,
    mode: PlanModeV1,
    current_documents: tuple[CurrentDocumentRefsV1, ...],
    stage_pins: Mapping[FormalStageV1, StagePinsV1],
    cached_receipts: tuple[StageReceiptV1, ...] = (),
    dev_document_ids: tuple[str, ...] = (),
) -> IncrementalFormalPlanV1:
    """Plan the smallest new work frontier without executing or mutating it."""

    if type(mode) is not PlanModeV1:
        raise _error("formal plan mode must be one exact PlanModeV1")
    if type(current_documents) is not tuple or not current_documents:
        raise _error("current document denominator must be one nonempty tuple")
    for document in current_documents:
        _validate_document(document)
    ordinals = tuple(item.document_ordinal for item in current_documents)
    ids = tuple(item.document_id for item in current_documents)
    if ordinals != tuple(range(1, len(current_documents) + 1)) or len(set(ids)) != len(ids):
        raise _error("current documents must have contiguous order and unique IDs")
    if (
        type(stage_pins) is not dict
        or any(type(stage) is not FormalStageV1 for stage in stage_pins)
        or set(stage_pins) != set(_STAGE_ORDER)
    ):
        raise _error("stage pins must cover the exact formal DAG")
    for stage in _STAGE_ORDER:
        _validate_pins(stage, stage_pins[stage])
    if type(dev_document_ids) is not tuple or any(
        type(item) is not str for item in dev_document_ids
    ):
        raise _error("DEV_FAST document IDs must be one tuple of strings")
    id_set = set(ids)
    if mode is PlanModeV1.DEV_FAST:
        if not dev_document_ids or len(set(dev_document_ids)) != len(dev_document_ids):
            raise _error("DEV_FAST requires a nonempty unique document subset")
        unknown = set(dev_document_ids) - id_set
        if unknown:
            raise _error(f"DEV_FAST contains unknown documents: {sorted(unknown)}")
        selected_id_set = set(dev_document_ids)
        selected_ids = tuple(item for item in ids if item in selected_id_set)
    else:
        if dev_document_ids:
            raise _error(f"{mode.value} always uses the complete current document denominator")
        selected_ids = ids

    if type(cached_receipts) is not tuple:
        raise _error("cached receipts must be one tuple")
    cache: dict[tuple[str, FormalStageV1], list[StageReceiptV1]] = {}
    cache_keys: set[tuple[str, FormalStageV1, str]] = set()
    for raw in cached_receipts:
        receipt = _validate_receipt(raw)
        if receipt.document_id not in id_set:
            raise _error(f"cached receipt belongs to unknown document {receipt.document_id}")
        content_key = (receipt.document_id, receipt.stage, receipt.stage_key)
        if content_key in cache_keys:
            raise _error(
                "cached receipts repeat one content-addressed key for "
                f"{receipt.document_id}/{receipt.stage.value}"
            )
        cache_keys.add(content_key)
        cache.setdefault((receipt.document_id, receipt.stage), []).append(receipt)

    by_id = {item.document_id: item for item in current_documents}
    decisions: list[PlannedStageV1] = []
    for document_id in selected_ids:
        document = by_id[document_id]
        accepted: dict[FormalStageV1, StageReceiptV1] = {}
        graph_outcome: StageOutcomeV1 | None = None
        for stage in _STAGE_ORDER:
            if stage is FormalStageV1.SEAL and mode is not PlanModeV1.RELEASE_SEAL:
                decisions.append(
                    _skipped(
                        document_id,
                        stage,
                        "MODE_EXCLUDES_RELEASE_SEAL",
                        f"{mode.value} never emits release authority",
                    )
                )
                continue
            if (
                stage is FormalStageV1.GEMMA_RESCUE
                and graph_outcome is not StageOutcomeV1.GRAPH_RESCUE_REQUIRED
            ):
                if FormalStageV1.GRAPH not in accepted:
                    decisions.append(
                        _blocked(
                            document_id,
                            stage,
                            "UPSTREAM_GRAPH_OUTCOME_UNKNOWN",
                            "Gemma is conditional and waits for the deterministic graph outcome",
                        )
                    )
                else:
                    decisions.append(
                        _skipped(
                            document_id,
                            stage,
                            "DETERMINISTIC_GRAPH_DID_NOT_REQUEST_RESCUE",
                            "Gemma remains unused when deterministic structure is decisive",
                        )
                    )
                continue
            if (
                stage is FormalStageV1.NUMERIC_PIXEL
                and graph_outcome is StageOutcomeV1.GRAPH_NOT_OBSERVED
            ):
                decisions.append(
                    _skipped(
                        document_id,
                        stage,
                        "COMPLETE_DOCUMENT_NEGATIVE_HAS_NO_NUMERIC_CELLS",
                        "a coverage-bound absent family does not run numeric/pixel work",
                    )
                )
                continue
            parents = _parents_for_stage(stage, graph_outcome)
            missing = tuple(parent for parent in parents if parent not in accepted)
            if missing:
                decisions.append(
                    _blocked(
                        document_id,
                        stage,
                        "UPSTREAM_RECOMPUTE_REQUIRED",
                        "waiting for exact outputs: " + ", ".join(item.value for item in missing),
                    )
                )
                continue
            if stage is FormalStageV1.SEAL:
                mapping = accepted[FormalStageV1.MAPPING]
                if mapping.outcome is not StageOutcomeV1.MAPPING_RESOLVED:
                    decisions.append(
                        _blocked(
                            document_id,
                            stage,
                            "TERMINAL_MAPPING_UNRESOLVED",
                            "release sealing requires a resolved mapping outcome",
                        )
                    )
                    continue
            node = _expected_node(
                document,
                stage,
                stage_pins[stage],
                accepted,
                graph_outcome,
            )
            decision, hit = _candidate_decision(
                node,
                document,
                tuple(cache.get((document_id, stage), ())),
            )
            decisions.append(decision)
            if hit is not None:
                accepted[stage] = hit
                if stage is FormalStageV1.GRAPH:
                    graph_outcome = hit.outcome

    active = tuple(item for item in decisions if item.decision is not CacheDecisionV1.SKIPPED)
    ready = bool(active) and all(item.decision is CacheDecisionV1.HIT for item in active)
    return IncrementalFormalPlanV1(
        FORMAT_VERSION,
        mode,
        len(current_documents),
        selected_ids,
        tuple(decisions),
        ready,
    )


def stage_invalidation_closure_v1(
    changed_stages: Iterable[FormalStageV1],
    *,
    rescue_possible: bool = True,
    include_release_seal: bool = True,
) -> tuple[FormalStageV1, ...]:
    """Return the static downstream closure used to explain pin invalidation.

    The runtime planner can be narrower (for example, an already proven absent
    document skips numeric and Gemma), while this helper is the conservative
    reusable closure for change review.
    """

    if type(rescue_possible) is not bool or type(include_release_seal) is not bool:
        raise _error("invalidation closure flags must be exact booleans")
    pending: list[FormalStageV1] = []
    for stage in changed_stages:
        if type(stage) is not FormalStageV1:
            raise _error("changed stages must contain exact FormalStageV1 values")
        pending.append(stage)
    invalid = set(pending)
    while pending:
        current = pending.pop()
        for child in _STATIC_CHILDREN[current]:
            if child not in invalid:
                invalid.add(child)
                pending.append(child)
    if not rescue_possible:
        invalid.discard(FormalStageV1.GEMMA_RESCUE)
    if not include_release_seal:
        invalid.discard(FormalStageV1.SEAL)
    return tuple(stage for stage in _STAGE_ORDER if stage in invalid)
