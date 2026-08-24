"""Fail-closed runtime lifecycle for the incremental formal DAG.

V1 remains the pure content-addressed DAG/cache planner.  This V2 module adds
the execution controls that must not be optional at a formal boundary:

* one complete, immutable failure ledger (explicitly verified-empty or closed),
* a predeclared runtime budget bound to the exact algorithm pin vector,
* an append-only failure/success lifecycle that can converge,
* revision probation restricted to documents implicated by historical failure,
* and an explicit non-authoritative release state when caller-current refs are
  absent or stale.

The module still does not authenticate files, execute a stage, measure a clock,
or write a cache.  Millisecond observations and content refs are caller-owned
evidence and require authentication outside this bookkeeping boundary.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from bctc_ai.evaluation.incremental_formal_dag_v1 import (
    CacheDecisionV1,
    ContentRefKindV1,
    CurrentDocumentRefsV1,
    DependencyRefV1,
    FormalStageV1,
    PageCoverageBoundV1,
    PlanModeV1,
    PlannedStageV1,
    StageOutcomeV1,
    StagePinsV1,
    StageReceiptV1,
    TypedContentRefV1,
    build_stage_receipt_v1,
    plan_incremental_formal_dag_v1,
    stage_invalidation_closure_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
)

__all__ = [
    "FORMAT_VERSION",
    "CLAIM_BOUNDARY",
    "AuthorityRefKindV2",
    "CallerCurrentRefsV2",
    "FailureLedgerStateV2",
    "FailureLedgerV2",
    "FailureTaxonomyV2",
    "HistoricalCountersV2",
    "IncrementalFormalRuntimePlanV2",
    "IncrementalFormalRuntimeV2Error",
    "LifecycleActionV2",
    "PlannedRuntimeStageV2",
    "ReleaseAuthorityV2",
    "RuntimeAuthorityRefV2",
    "RuntimeObservationKindV2",
    "RuntimeObservationV2",
    "RuntimePreflightV2",
    "RuntimeScopeV2",
    "StageRevisionV2",
    "SuccessPurposeV2",
    "append_stage_failure_v2",
    "append_targeted_success_v2",
    "build_caller_current_refs_v2",
    "build_runtime_preflight_v2",
    "build_targeted_stage_receipt_v2",
    "build_verified_empty_failure_ledger_v2",
    "plan_incremental_formal_runtime_v2",
    "validate_failure_ledger_v2",
]


FORMAT_VERSION = "FAMILY_FIRST_INCREMENTAL_FORMAL_RUNTIME_V2"
_LEDGER_FORMAT_VERSION = "FAMILY_FIRST_FAILURE_LEDGER_V2"
_OBSERVATION_FORMAT_VERSION = "FAMILY_FIRST_RUNTIME_OBSERVATION_V2"
_PREFLIGHT_FORMAT_VERSION = "FAMILY_FIRST_RUNTIME_PREFLIGHT_V2"
_CALLER_REFS_FORMAT_VERSION = "FAMILY_FIRST_CALLER_CURRENT_REFS_V2"
CLAIM_BOUNDARY = (
    "CONTENT_BOOKKEEPING_ONLY_NON_AUTHORITATIVE_UNTIL_CALLER_AUTHENTICATES_"
    "CURRENT_REFS_LEDGER_STAGE_OUTPUTS_AND_EXECUTION_TIMING"
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GENERIC_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_STAGE_KEY = re.compile(r"^ffifdv1:stage:[0-9a-f]{64}$")
_RECEIPT_ID = re.compile(r"^ffifdv1:receipt:[0-9a-f]{64}$")
_REVISION_KEY = re.compile(r"^ffirv2:algorithm:[0-9a-f]{64}$")
_PREFLIGHT_ID = re.compile(r"^ffirv2:preflight:[0-9a-f]{64}$")
_OBSERVATION_ID = re.compile(r"^ffirv2:observation:[0-9a-f]{64}$")
_LEDGER_ID = re.compile(r"^ffirv2:ledger:[0-9a-f]{64}$")
_CALLER_REFS_ID = re.compile(r"^ffirv2:current:[0-9a-f]{64}$")


class IncrementalFormalRuntimeV2Error(ValueError):
    """A V2 ledger, preflight, current-ref set, or lifecycle request drifted."""


class RuntimeScopeV2(StrEnum):
    FOCUSED = "FOCUSED"
    TARGETED = "TARGETED"
    FAMILY_140_COLD = "FAMILY_140_COLD"


class FailureLedgerStateV2(StrEnum):
    VERIFIED_EMPTY = "VERIFIED_EMPTY"
    CLOSED = "CLOSED"


class RuntimeObservationKindV2(StrEnum):
    STAGE_FAILURE = "STAGE_FAILURE"
    TARGET_BUDGET_BREACH = "TARGET_BUDGET_BREACH"
    HARD_BUDGET_BREACH = "HARD_BUDGET_BREACH"
    TARGETED_SUCCESS = "TARGETED_SUCCESS"


class SuccessPurposeV2(StrEnum):
    INCIDENT_RESOLUTION = "INCIDENT_RESOLUTION"
    REVISION_PROBATION = "REVISION_PROBATION"
    INCIDENT_AND_REVISION_PROBATION = "INCIDENT_AND_REVISION_PROBATION"


class FailureTaxonomyV2(StrEnum):
    """Closed, bank-agnostic failure classes; callers cannot mint synonyms."""

    SOURCE_AUTHENTICATION = "SOURCE_AUTHENTICATION"
    OCR_OBSERVATION = "OCR_OBSERVATION"
    RETRIEVAL_COVERAGE = "RETRIEVAL_COVERAGE"
    OWNER_BOUNDARY = "OWNER_BOUNDARY"
    ROW_TOPOLOGY = "ROW_TOPOLOGY"
    COLUMN_AXIS = "COLUMN_AXIS"
    PERIOD_AXIS = "PERIOD_AXIS"
    UNIT_AXIS = "UNIT_AXIS"
    NUMERIC_PARSE = "NUMERIC_PARSE"
    SCHEMA_MAPPING = "SCHEMA_MAPPING"
    ACCOUNTING_CLOSURE = "ACCOUNTING_CLOSURE"
    OUTPUT_INTEGRITY = "OUTPUT_INTEGRITY"
    INTERNAL_CONTRACT = "INTERNAL_CONTRACT"
    RUNTIME_TARGET_BREACH = "RUNTIME_TARGET_BREACH"
    RUNTIME_HARD_BREACH = "RUNTIME_HARD_BREACH"


_NON_RUNTIME_FAILURES = frozenset(
    item
    for item in FailureTaxonomyV2
    if item
    not in {
        FailureTaxonomyV2.RUNTIME_TARGET_BREACH,
        FailureTaxonomyV2.RUNTIME_HARD_BREACH,
    }
)


class LifecycleActionV2(StrEnum):
    BASE_DAG_DECISION = "BASE_DAG_DECISION"
    TARGETED_RETRY_REQUIRED = "TARGETED_RETRY_REQUIRED"
    REVISION_PROBATION_REQUIRED = "REVISION_PROBATION_REQUIRED"
    TARGETED_RETRY_AND_REVISION_PROBATION = (
        "TARGETED_RETRY_AND_REVISION_PROBATION"
    )
    TARGETED_PREFLIGHT_REQUIRED = "TARGETED_PREFLIGHT_REQUIRED"
    REVISION_PROBATION_PENDING_ELSEWHERE = "REVISION_PROBATION_PENDING_ELSEWHERE"
    ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE = (
        "ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE"
    )
    ALGORITHM_REVIEW_REQUIRED_TARGET_BUDGET = (
        "ALGORITHM_REVIEW_REQUIRED_TARGET_BUDGET"
    )
    ALGORITHM_REVIEW_REQUIRED_HARD_BUDGET = (
        "ALGORITHM_REVIEW_REQUIRED_HARD_BUDGET"
    )
    UPSTREAM_LIFECYCLE_PENDING = "UPSTREAM_LIFECYCLE_PENDING"


class ReleaseAuthorityV2(StrEnum):
    NOT_RELEASE_MODE = "NOT_RELEASE_MODE"
    NON_AUTHORITATIVE_MISSING_CALLER_CURRENT_REFS = (
        "NON_AUTHORITATIVE_MISSING_CALLER_CURRENT_REFS"
    )
    NON_AUTHORITATIVE_CALLER_CURRENT_REF_DRIFT = (
        "NON_AUTHORITATIVE_CALLER_CURRENT_REF_DRIFT"
    )
    NON_AUTHORITATIVE_EXECUTION_INCOMPLETE = (
        "NON_AUTHORITATIVE_EXECUTION_INCOMPLETE"
    )
    CALLER_CURRENT_BOUND_RELEASE_CANDIDATE = (
        "CALLER_CURRENT_BOUND_RELEASE_CANDIDATE"
    )


class AuthorityRefKindV2(StrEnum):
    DOCUMENT_MANIFEST = "DOCUMENT_MANIFEST"
    CACHE_MANIFEST = "CACHE_MANIFEST"
    FAILURE_LEDGER = "FAILURE_LEDGER"


_STAGE_ORDER = tuple(FormalStageV1)


@dataclass(frozen=True, slots=True)
class RuntimeAuthorityRefV2:
    kind: AuthorityRefKindV2
    logical_id: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class CallerCurrentRefsV2:
    format_version: str
    claim_boundary: str
    document_manifest_ref: RuntimeAuthorityRefV2
    cache_manifest_ref: RuntimeAuthorityRefV2
    failure_ledger_ref: RuntimeAuthorityRefV2
    caller_current_id: str


@dataclass(frozen=True, slots=True)
class StageRevisionV2:
    stage: FormalStageV1
    algorithm_revision_key: str


@dataclass(frozen=True, slots=True)
class RuntimePreflightV2:
    format_version: str
    claim_boundary: str
    family_id: str
    scope: RuntimeScopeV2
    selected_document_ids: tuple[str, ...]
    document_manifest_ref: RuntimeAuthorityRefV2
    cache_manifest_ref: RuntimeAuthorityRefV2
    failure_ledger_ref: RuntimeAuthorityRefV2
    stage_revisions: tuple[StageRevisionV2, ...]
    target_budget_ms: int
    hard_budget_ms: int
    preflight_id: str


@dataclass(frozen=True, slots=True)
class RuntimeObservationV2:
    format_version: str
    claim_boundary: str
    sequence: int
    previous_observation_id: str | None
    family_id: str
    document_id: str
    stage: FormalStageV1
    algorithm_revision_key: str
    stage_key: str
    preflight_id: str
    scope: RuntimeScopeV2
    target_budget_ms: int
    hard_budget_ms: int
    kind: RuntimeObservationKindV2
    taxonomy: FailureTaxonomyV2 | None
    observed_runtime_ms: int
    success_purpose: SuccessPurposeV2 | None
    resolves_observation_ids: tuple[str, ...]
    result_receipt_id: str | None
    observation_id: str


@dataclass(frozen=True, slots=True)
class HistoricalCountersV2:
    stage_failure_count: int
    target_budget_breach_count: int
    hard_budget_breach_count: int
    targeted_success_count: int
    taxonomy_counts: tuple[tuple[FailureTaxonomyV2, int], ...]


@dataclass(frozen=True, slots=True)
class FailureLedgerV2:
    format_version: str
    claim_boundary: str
    family_id: str
    state: FailureLedgerStateV2
    observations: tuple[RuntimeObservationV2, ...]
    counters: HistoricalCountersV2
    head_observation_id: str | None
    ledger_id: str


@dataclass(frozen=True, slots=True)
class PlannedRuntimeStageV2:
    base_stage: PlannedStageV1
    decision: CacheDecisionV1
    lifecycle_action: LifecycleActionV2
    algorithm_revision_key: str
    preflight_id: str
    resolution_target_ids: tuple[str, ...]

    @property
    def document_id(self) -> str:
        return self.base_stage.document_id

    @property
    def stage(self) -> FormalStageV1:
        return self.base_stage.stage

    @property
    def expected_stage_key(self) -> str | None:
        return self.base_stage.expected_stage_key

    @property
    def expected_dependencies(self) -> tuple[DependencyRefV1, ...]:
        return self.base_stage.expected_dependencies

    @property
    def cached_receipt_id(self) -> str | None:
        return self.base_stage.cached_receipt_id


@dataclass(frozen=True, slots=True)
class IncrementalFormalRuntimePlanV2:
    format_version: str
    mode: PlanModeV1
    scope: RuntimeScopeV2
    current_document_count: int
    selected_document_ids: tuple[str, ...]
    decisions: tuple[PlannedRuntimeStageV2, ...]
    execution_ready: bool
    ready: bool
    release_authority: ReleaseAuthorityV2
    historical_counters: HistoricalCountersV2

    @property
    def runnable(self) -> tuple[PlannedRuntimeStageV2, ...]:
        return tuple(
            item for item in self.decisions if item.decision is CacheDecisionV1.RECOMPUTE
        )

    @property
    def cache_hits(self) -> tuple[PlannedRuntimeStageV2, ...]:
        return tuple(item for item in self.decisions if item.decision is CacheDecisionV1.HIT)

    @property
    def algorithm_review_required(self) -> bool:
        return any(
            item.lifecycle_action
            in {
                LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE,
                LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_TARGET_BUDGET,
                LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_HARD_BUDGET,
            }
            for item in self.decisions
        )


def _error(message: str) -> IncrementalFormalRuntimeV2Error:
    return IncrementalFormalRuntimeV2Error(message)


def _validate_generic_id(value: Any, label: str) -> str:
    if type(value) is not str or _GENERIC_ID.fullmatch(value) is None:
        raise _error(f"{label} must be one stable uppercase identifier")
    return value


def _validate_exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _error(f"{label} must be one exact integer >= {minimum}")
    return value


def _v1_ref_payload(value: TypedContentRefV1) -> dict[str, Any]:
    if type(value) is not TypedContentRefV1 or type(value.kind) is not ContentRefKindV1:
        raise _error("V1 content ref must retain its exact type")
    if (
        type(value.logical_id) is not str
        or not value.logical_id
        or type(value.sha256) is not str
        or _SHA256.fullmatch(value.sha256) is None
        or type(value.size_bytes) is not int
        or value.size_bytes < 0
    ):
        raise _error("V1 content ref identity drifted")
    return {
        "kind": value.kind.value,
        "logical_id": value.logical_id,
        "sha256": value.sha256,
        "size_bytes": value.size_bytes,
    }


def _authority_ref_payload(value: RuntimeAuthorityRefV2) -> dict[str, Any]:
    _validate_authority_ref(value)
    return {
        "kind": value.kind.value,
        "logical_id": value.logical_id,
        "sha256": value.sha256,
        "size_bytes": value.size_bytes,
    }


def _validate_authority_ref(
    value: Any, expected_kind: AuthorityRefKindV2 | None = None
) -> RuntimeAuthorityRefV2:
    if type(value) is not RuntimeAuthorityRefV2 or type(value.kind) is not AuthorityRefKindV2:
        raise _error("runtime authority ref must retain its exact type")
    if expected_kind is not None and value.kind is not expected_kind:
        raise _error("runtime authority ref kind drifted")
    if (
        type(value.logical_id) is not str
        or not value.logical_id
        or value.logical_id != value.logical_id.strip()
        or type(value.sha256) is not str
        or _SHA256.fullmatch(value.sha256) is None
        or type(value.size_bytes) is not int
        or value.size_bytes < 0
    ):
        raise _error("runtime authority ref identity drifted")
    return value


def _content_ref(kind: AuthorityRefKindV2, logical_id: str, material: Any) -> RuntimeAuthorityRefV2:
    payload = canonical_json_bytes_v1(material)
    return RuntimeAuthorityRefV2(kind, logical_id, canonical_json_sha256_v1(material), len(payload))


def _document_manifest_ref(
    current_documents: tuple[CurrentDocumentRefsV1, ...],
) -> RuntimeAuthorityRefV2:
    if type(current_documents) is not tuple or not current_documents:
        raise _error("current documents must be one nonempty exact tuple")
    rows: list[dict[str, Any]] = []
    for document in current_documents:
        if type(document) is not CurrentDocumentRefsV1:
            raise _error("current document must retain its exact V1 type")
        if (
            type(document.document_ordinal) is not int
            or document.document_ordinal <= 0
            or type(document.document_id) is not str
            or not document.document_id
            or type(document.page_count) is not int
            or document.page_count <= 0
        ):
            raise _error("current document identity drifted")
        rows.append(
            {
                "document_ordinal": document.document_ordinal,
                "document_id": document.document_id,
                "document_packet_ref": _v1_ref_payload(document.document_packet_ref),
                "source_pdf_ref": _v1_ref_payload(document.source_pdf_ref),
                "page_set_ref": _v1_ref_payload(document.page_set_ref),
                "page_count": document.page_count,
            }
        )
    if tuple(item["document_ordinal"] for item in rows) != tuple(range(1, len(rows) + 1)):
        raise _error("current document ordinals must be contiguous")
    if len({item["document_id"] for item in rows}) != len(rows):
        raise _error("current document IDs must be unique")
    material = {"format_version": FORMAT_VERSION, "documents": rows}
    return _content_ref(
        AuthorityRefKindV2.DOCUMENT_MANIFEST,
        "ffirv2/current/document-manifest",
        material,
    )


def _cache_manifest_ref(cached_receipts: tuple[StageReceiptV1, ...]) -> RuntimeAuthorityRefV2:
    if type(cached_receipts) is not tuple:
        raise _error("cached receipts must be one exact tuple")
    rows: list[dict[str, str]] = []
    for receipt in cached_receipts:
        if type(receipt) is not StageReceiptV1:
            raise _error("cached receipt must retain its exact V1 type")
        if (
            type(receipt.document_id) is not str
            or type(receipt.stage) is not FormalStageV1
            or type(receipt.stage_key) is not str
            or _STAGE_KEY.fullmatch(receipt.stage_key) is None
            or type(receipt.receipt_id) is not str
            or _RECEIPT_ID.fullmatch(receipt.receipt_id) is None
        ):
            raise _error("cached receipt identity drifted before preflight")
        rows.append(
            {
                "document_id": receipt.document_id,
                "stage": receipt.stage.value,
                "stage_key": receipt.stage_key,
                "receipt_id": receipt.receipt_id,
            }
        )
    rows.sort(key=lambda item: (item["document_id"], item["stage"], item["stage_key"]))
    material = {"format_version": FORMAT_VERSION, "receipts": rows}
    return _content_ref(
        AuthorityRefKindV2.CACHE_MANIFEST,
        "ffirv2/current/cache-manifest",
        material,
    )


def _pin_revision(stage: FormalStageV1, pins: StagePinsV1) -> StageRevisionV2:
    if type(stage) is not FormalStageV1 or type(pins) is not StagePinsV1:
        raise _error("stage revision requires exact V1 stage and pins")
    categories: list[dict[str, Any]] = []
    for name, expected_kind, refs, allow_empty in (
        ("algorithm", ContentRefKindV1.CODE, pins.code_refs, False),
        ("spec", ContentRefKindV1.SPEC, pins.spec_refs, True),
        ("model", ContentRefKindV1.MODEL, pins.model_refs, True),
        ("prompt", ContentRefKindV1.PROMPT, pins.prompt_refs, True),
    ):
        if type(refs) is not tuple or (not allow_empty and not refs):
            raise _error(f"{stage.value} {name} pins must be one exact tuple")
        payloads = tuple(_v1_ref_payload(item) for item in refs)
        if any(item.kind is not expected_kind for item in refs):
            raise _error(f"{stage.value} {name} pin kind drifted")
        order = tuple((item.logical_id, item.sha256, item.size_bytes) for item in refs)
        if order != tuple(sorted(set(order))):
            raise _error(f"{stage.value} {name} pins must be sorted and unique")
        categories.append({"category": name, "refs": list(payloads)})
    material = {
        "format_version": FORMAT_VERSION,
        "stage": stage.value,
        "pin_categories": categories,
    }
    return StageRevisionV2(
        stage,
        f"ffirv2:algorithm:{canonical_json_sha256_v1(material)}",
    )


def _stage_revisions(
    stage_pins: dict[FormalStageV1, StagePinsV1],
) -> tuple[StageRevisionV2, ...]:
    if type(stage_pins) is not dict or set(stage_pins) != set(_STAGE_ORDER):
        raise _error("stage pins must be one exact dict covering the V1 DAG")
    return tuple(_pin_revision(stage, stage_pins[stage]) for stage in _STAGE_ORDER)


def _budget_for_scope(scope: RuntimeScopeV2) -> tuple[int, int]:
    if type(scope) is not RuntimeScopeV2:
        raise _error("runtime scope must retain its exact enum type")
    if scope is RuntimeScopeV2.FOCUSED:
        return 9_999, 9_999
    if scope is RuntimeScopeV2.TARGETED:
        return 29_999, 29_999
    return 180_000, 300_000


def _counter_payload(value: HistoricalCountersV2) -> dict[str, Any]:
    return {
        "stage_failure_count": value.stage_failure_count,
        "target_budget_breach_count": value.target_budget_breach_count,
        "hard_budget_breach_count": value.hard_budget_breach_count,
        "targeted_success_count": value.targeted_success_count,
        "taxonomy_counts": [[taxonomy.value, count] for taxonomy, count in value.taxonomy_counts],
    }


def _observation_payload(value: RuntimeObservationV2, *, include_id: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format_version": value.format_version,
        "claim_boundary": value.claim_boundary,
        "sequence": value.sequence,
        "previous_observation_id": value.previous_observation_id,
        "family_id": value.family_id,
        "document_id": value.document_id,
        "stage": value.stage.value,
        "algorithm_revision_key": value.algorithm_revision_key,
        "stage_key": value.stage_key,
        "preflight_id": value.preflight_id,
        "scope": value.scope.value,
        "target_budget_ms": value.target_budget_ms,
        "hard_budget_ms": value.hard_budget_ms,
        "kind": value.kind.value,
        "taxonomy": value.taxonomy.value if value.taxonomy is not None else None,
        "observed_runtime_ms": value.observed_runtime_ms,
        "success_purpose": (
            value.success_purpose.value if value.success_purpose is not None else None
        ),
        "resolves_observation_ids": list(value.resolves_observation_ids),
        "result_receipt_id": value.result_receipt_id,
    }
    if include_id:
        payload["observation_id"] = value.observation_id
    return payload


def _observation_id(value: RuntimeObservationV2) -> str:
    return f"ffirv2:observation:{canonical_json_sha256_v1(_observation_payload(value, include_id=False))}"


def _compute_counters(
    observations: tuple[RuntimeObservationV2, ...],
) -> HistoricalCountersV2:
    kinds = Counter(item.kind for item in observations)
    taxonomy = Counter(item.taxonomy for item in observations if item.taxonomy is not None)
    return HistoricalCountersV2(
        kinds[RuntimeObservationKindV2.STAGE_FAILURE],
        kinds[RuntimeObservationKindV2.TARGET_BUDGET_BREACH],
        kinds[RuntimeObservationKindV2.HARD_BUDGET_BREACH],
        kinds[RuntimeObservationKindV2.TARGETED_SUCCESS],
        tuple(sorted(taxonomy.items(), key=lambda item: item[0].value)),
    )


def _validate_counters_exact(value: HistoricalCountersV2) -> None:
    for label, count in (
        ("stage failure", value.stage_failure_count),
        ("target-budget breach", value.target_budget_breach_count),
        ("hard-budget breach", value.hard_budget_breach_count),
        ("targeted success", value.targeted_success_count),
    ):
        _validate_exact_int(count, f"historical {label} count")
    if type(value.taxonomy_counts) is not tuple:
        raise _error("historical taxonomy counts must be one exact tuple")
    previous: str | None = None
    for item in value.taxonomy_counts:
        if (
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not FailureTaxonomyV2
            or type(item[1]) is not int
            or item[1] <= 0
            or (previous is not None and item[0].value <= previous)
        ):
            raise _error("historical taxonomy counter shape/order drifted")
        previous = item[0].value


def _ledger_payload(value: FailureLedgerV2, *, include_id: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format_version": value.format_version,
        "claim_boundary": value.claim_boundary,
        "family_id": value.family_id,
        "state": value.state.value,
        "observations": [
            _observation_payload(item, include_id=True) for item in value.observations
        ],
        "counters": _counter_payload(value.counters),
        "head_observation_id": value.head_observation_id,
    }
    if include_id:
        payload["ledger_id"] = value.ledger_id
    return payload


def _ledger_id(value: FailureLedgerV2) -> str:
    return f"ffirv2:ledger:{canonical_json_sha256_v1(_ledger_payload(value, include_id=False))}"


def _failure_ledger_ref(ledger: FailureLedgerV2) -> RuntimeAuthorityRefV2:
    validate_failure_ledger_v2(ledger)
    material = _ledger_payload(ledger, include_id=True)
    return _content_ref(
        AuthorityRefKindV2.FAILURE_LEDGER,
        f"ffirv2/current/failure-ledger/{ledger.family_id}",
        material,
    )


def build_verified_empty_failure_ledger_v2(*, family_id: str) -> FailureLedgerV2:
    """Mint an explicit, content-bound empty ledger; omission is never equivalent."""

    _validate_generic_id(family_id, "family ID")
    counters = _compute_counters(())
    provisional = FailureLedgerV2(
        _LEDGER_FORMAT_VERSION,
        CLAIM_BOUNDARY,
        family_id,
        FailureLedgerStateV2.VERIFIED_EMPTY,
        (),
        counters,
        None,
        "",
    )
    result = replace(provisional, ledger_id=_ledger_id(provisional))
    return validate_failure_ledger_v2(result)


def _validate_observation(
    value: Any,
    *,
    family_id: str,
    expected_sequence: int,
    expected_previous: str | None,
    prior_by_id: dict[str, RuntimeObservationV2],
    incident_resolutions: set[str],
    probation_resolutions: set[tuple[str, FormalStageV1, str]],
) -> RuntimeObservationV2:
    if type(value) is not RuntimeObservationV2:
        raise _error("ledger observation must retain its exact V2 type")
    if (
        value.format_version != _OBSERVATION_FORMAT_VERSION
        or value.claim_boundary != CLAIM_BOUNDARY
        or type(value.sequence) is not int
        or value.sequence != expected_sequence
        or value.previous_observation_id != expected_previous
        or value.family_id != family_id
        or type(value.document_id) is not str
        or not value.document_id
        or value.document_id != value.document_id.strip()
        or type(value.stage) is not FormalStageV1
        or type(value.algorithm_revision_key) is not str
        or _REVISION_KEY.fullmatch(value.algorithm_revision_key) is None
        or type(value.stage_key) is not str
        or _STAGE_KEY.fullmatch(value.stage_key) is None
        or type(value.preflight_id) is not str
        or _PREFLIGHT_ID.fullmatch(value.preflight_id) is None
        or type(value.scope) is not RuntimeScopeV2
        or type(value.kind) is not RuntimeObservationKindV2
    ):
        raise _error("runtime observation identity drifted")
    target_budget, hard_budget = _budget_for_scope(value.scope)
    if (
        type(value.target_budget_ms) is not int
        or value.target_budget_ms != target_budget
        or type(value.hard_budget_ms) is not int
        or value.hard_budget_ms != hard_budget
        or type(value.observed_runtime_ms) is not int
        or value.observed_runtime_ms < 0
        or type(value.resolves_observation_ids) is not tuple
        or any(type(item) is not str for item in value.resolves_observation_ids)
        or tuple(sorted(set(value.resolves_observation_ids)))
        != value.resolves_observation_ids
    ):
        raise _error("runtime observation budget or resolution shape drifted")

    if value.kind is RuntimeObservationKindV2.STAGE_FAILURE:
        if (
            type(value.taxonomy) is not FailureTaxonomyV2
            or value.taxonomy not in _NON_RUNTIME_FAILURES
            or value.observed_runtime_ms > target_budget
            or value.success_purpose is not None
            or value.resolves_observation_ids
            or value.result_receipt_id is not None
        ):
            raise _error("ordinary stage failure taxonomy/runtime shape drifted")
    elif value.kind is RuntimeObservationKindV2.TARGET_BUDGET_BREACH:
        if (
            value.taxonomy is not FailureTaxonomyV2.RUNTIME_TARGET_BREACH
            or not target_budget < value.observed_runtime_ms <= hard_budget
            or value.success_purpose is not None
            or value.resolves_observation_ids
            or value.result_receipt_id is not None
        ):
            raise _error("target-budget breach shape drifted")
    elif value.kind is RuntimeObservationKindV2.HARD_BUDGET_BREACH:
        if (
            value.taxonomy is not FailureTaxonomyV2.RUNTIME_HARD_BREACH
            or value.observed_runtime_ms <= hard_budget
            or value.success_purpose is not None
            or value.resolves_observation_ids
            or value.result_receipt_id is not None
        ):
            raise _error("hard-budget breach shape drifted")
    else:
        if (
            value.taxonomy is not None
            or type(value.success_purpose) is not SuccessPurposeV2
            or not value.resolves_observation_ids
            or value.observed_runtime_ms > target_budget
            or type(value.result_receipt_id) is not str
            or _RECEIPT_ID.fullmatch(value.result_receipt_id) is None
        ):
            raise _error("targeted success shape drifted")
        targets: list[RuntimeObservationV2] = []
        for target_id in value.resolves_observation_ids:
            target = prior_by_id.get(target_id)
            if target is None or target.kind is RuntimeObservationKindV2.TARGETED_SUCCESS:
                raise _error("targeted success must resolve prior failure/budget observations")
            if target.document_id != value.document_id or target.stage is not value.stage:
                raise _error("targeted success resolution crosses document or stage")
            targets.append(target)
        current_targets = tuple(
            item for item in targets if item.algorithm_revision_key == value.algorithm_revision_key
        )
        prior_targets = tuple(
            item for item in targets if item.algorithm_revision_key != value.algorithm_revision_key
        )
        expected_purpose = (
            SuccessPurposeV2.INCIDENT_AND_REVISION_PROBATION
            if current_targets and prior_targets
            else SuccessPurposeV2.INCIDENT_RESOLUTION
            if current_targets
            else SuccessPurposeV2.REVISION_PROBATION
        )
        if value.success_purpose is not expected_purpose:
            raise _error("targeted success purpose does not match its resolution revisions")
        for target in current_targets:
            if target.kind is RuntimeObservationKindV2.HARD_BUDGET_BREACH:
                raise _error("a same-revision hard breach requires algorithm review")
            if target.observation_id in incident_resolutions:
                raise _error("one incident cannot be resolved twice")
            incident_resolutions.add(target.observation_id)
        if prior_targets:
            probation_key = (value.document_id, value.stage, value.algorithm_revision_key)
            if probation_key in probation_resolutions:
                raise _error("one document/stage/revision probation cannot close twice")
            probation_resolutions.add(probation_key)

    if type(value.observation_id) is not str or value.observation_id != _observation_id(value):
        raise _error("runtime observation content identity drifted")
    return value


def validate_failure_ledger_v2(value: Any) -> FailureLedgerV2:
    """Validate exact types, append order, hash chain, counters, and closure."""

    if type(value) is not FailureLedgerV2:
        raise _error("failure ledger is mandatory and must retain its exact V2 type")
    if (
        value.format_version != _LEDGER_FORMAT_VERSION
        or value.claim_boundary != CLAIM_BOUNDARY
        or type(value.state) is not FailureLedgerStateV2
        or type(value.observations) is not tuple
        or type(value.counters) is not HistoricalCountersV2
    ):
        raise _error("failure ledger format/state drifted")
    _validate_generic_id(value.family_id, "failure-ledger family ID")
    _validate_counters_exact(value.counters)
    prior_by_id: dict[str, RuntimeObservationV2] = {}
    incident_resolutions: set[str] = set()
    probation_resolutions: set[tuple[str, FormalStageV1, str]] = set()
    previous: str | None = None
    for sequence, observation in enumerate(value.observations, start=1):
        _validate_observation(
            observation,
            family_id=value.family_id,
            expected_sequence=sequence,
            expected_previous=previous,
            prior_by_id=prior_by_id,
            incident_resolutions=incident_resolutions,
            probation_resolutions=probation_resolutions,
        )
        if observation.observation_id in prior_by_id:
            raise _error("failure ledger repeats an observation identity")
        prior_by_id[observation.observation_id] = observation
        previous = observation.observation_id
    expected_counters = _compute_counters(value.observations)
    if value.counters != expected_counters:
        raise _error("failure ledger historical counters were rewritten")
    if value.state is FailureLedgerStateV2.VERIFIED_EMPTY:
        if value.observations or value.head_observation_id is not None:
            raise _error("VERIFIED_EMPTY ledger must be exactly empty")
    elif not value.observations or value.head_observation_id != previous:
        raise _error("CLOSED ledger must bind a nonempty complete observation head")
    if type(value.ledger_id) is not str or value.ledger_id != _ledger_id(value):
        raise _error("failure ledger content identity drifted")
    return value


def _close_ledger(
    ledger: FailureLedgerV2, observation: RuntimeObservationV2
) -> FailureLedgerV2:
    observations = (*ledger.observations, observation)
    provisional = FailureLedgerV2(
        _LEDGER_FORMAT_VERSION,
        CLAIM_BOUNDARY,
        ledger.family_id,
        FailureLedgerStateV2.CLOSED,
        observations,
        _compute_counters(observations),
        observation.observation_id,
        "",
    )
    return validate_failure_ledger_v2(replace(provisional, ledger_id=_ledger_id(provisional)))


def _caller_refs_payload(value: CallerCurrentRefsV2, *, include_id: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format_version": value.format_version,
        "claim_boundary": value.claim_boundary,
        "document_manifest_ref": _authority_ref_payload(value.document_manifest_ref),
        "cache_manifest_ref": _authority_ref_payload(value.cache_manifest_ref),
        "failure_ledger_ref": _authority_ref_payload(value.failure_ledger_ref),
    }
    if include_id:
        payload["caller_current_id"] = value.caller_current_id
    return payload


def _caller_refs_id(value: CallerCurrentRefsV2) -> str:
    return f"ffirv2:current:{canonical_json_sha256_v1(_caller_refs_payload(value, include_id=False))}"


def _validate_caller_current_refs(value: Any) -> CallerCurrentRefsV2:
    if type(value) is not CallerCurrentRefsV2:
        raise _error("caller-current refs must retain their exact V2 type")
    if value.format_version != _CALLER_REFS_FORMAT_VERSION or value.claim_boundary != CLAIM_BOUNDARY:
        raise _error("caller-current ref format drifted")
    _validate_authority_ref(value.document_manifest_ref, AuthorityRefKindV2.DOCUMENT_MANIFEST)
    _validate_authority_ref(value.cache_manifest_ref, AuthorityRefKindV2.CACHE_MANIFEST)
    _validate_authority_ref(value.failure_ledger_ref, AuthorityRefKindV2.FAILURE_LEDGER)
    if type(value.caller_current_id) is not str or value.caller_current_id != _caller_refs_id(value):
        raise _error("caller-current refs content identity drifted")
    return value


def build_caller_current_refs_v2(
    *,
    current_documents: tuple[CurrentDocumentRefsV1, ...],
    cached_receipts: tuple[StageReceiptV1, ...],
    failure_ledger: FailureLedgerV2,
) -> CallerCurrentRefsV2:
    """Project refs for caller authentication; projection alone grants no authority."""

    validate_failure_ledger_v2(failure_ledger)
    provisional = CallerCurrentRefsV2(
        _CALLER_REFS_FORMAT_VERSION,
        CLAIM_BOUNDARY,
        _document_manifest_ref(current_documents),
        _cache_manifest_ref(cached_receipts),
        _failure_ledger_ref(failure_ledger),
        "",
    )
    result = replace(provisional, caller_current_id=_caller_refs_id(provisional))
    return _validate_caller_current_refs(result)


def _preflight_payload(value: RuntimePreflightV2, *, include_id: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "format_version": value.format_version,
        "claim_boundary": value.claim_boundary,
        "family_id": value.family_id,
        "scope": value.scope.value,
        "selected_document_ids": list(value.selected_document_ids),
        "document_manifest_ref": _authority_ref_payload(value.document_manifest_ref),
        "cache_manifest_ref": _authority_ref_payload(value.cache_manifest_ref),
        "failure_ledger_ref": _authority_ref_payload(value.failure_ledger_ref),
        "stage_revisions": [
            {
                "stage": item.stage.value,
                "algorithm_revision_key": item.algorithm_revision_key,
            }
            for item in value.stage_revisions
        ],
        "target_budget_ms": value.target_budget_ms,
        "hard_budget_ms": value.hard_budget_ms,
    }
    if include_id:
        payload["preflight_id"] = value.preflight_id
    return payload


def _preflight_id(value: RuntimePreflightV2) -> str:
    return f"ffirv2:preflight:{canonical_json_sha256_v1(_preflight_payload(value, include_id=False))}"


def _validate_preflight(value: Any) -> RuntimePreflightV2:
    if type(value) is not RuntimePreflightV2:
        raise _error("runtime preflight is mandatory and must retain its exact V2 type")
    if (
        value.format_version != _PREFLIGHT_FORMAT_VERSION
        or value.claim_boundary != CLAIM_BOUNDARY
        or type(value.scope) is not RuntimeScopeV2
        or type(value.selected_document_ids) is not tuple
        or not value.selected_document_ids
        or any(
            type(item) is not str or not item or item != item.strip()
            for item in value.selected_document_ids
        )
        or len(set(value.selected_document_ids)) != len(value.selected_document_ids)
        or type(value.stage_revisions) is not tuple
    ):
        raise _error("runtime preflight identity/scope drifted")
    _validate_generic_id(value.family_id, "preflight family ID")
    _validate_authority_ref(value.document_manifest_ref, AuthorityRefKindV2.DOCUMENT_MANIFEST)
    _validate_authority_ref(value.cache_manifest_ref, AuthorityRefKindV2.CACHE_MANIFEST)
    _validate_authority_ref(value.failure_ledger_ref, AuthorityRefKindV2.FAILURE_LEDGER)
    if len(value.stage_revisions) != len(_STAGE_ORDER):
        raise _error("preflight must pin every formal stage revision")
    for expected_stage, revision in zip(_STAGE_ORDER, value.stage_revisions, strict=True):
        if (
            type(revision) is not StageRevisionV2
            or revision.stage is not expected_stage
            or type(revision.algorithm_revision_key) is not str
            or _REVISION_KEY.fullmatch(revision.algorithm_revision_key) is None
        ):
            raise _error("preflight stage revision vector drifted")
    target_budget, hard_budget = _budget_for_scope(value.scope)
    if (
        type(value.target_budget_ms) is not int
        or value.target_budget_ms != target_budget
        or type(value.hard_budget_ms) is not int
        or value.hard_budget_ms != hard_budget
    ):
        raise _error("preflight runtime budget is not the fixed policy")
    if value.scope is RuntimeScopeV2.FOCUSED and len(value.selected_document_ids) != 1:
        raise _error("FOCUSED preflight must bind exactly one document")
    if value.scope is RuntimeScopeV2.FAMILY_140_COLD and len(value.selected_document_ids) != 140:
        raise _error("FAMILY_140_COLD preflight must bind exactly 140 documents")
    if type(value.preflight_id) is not str or value.preflight_id != _preflight_id(value):
        raise _error("runtime preflight content identity drifted")
    return value


def build_runtime_preflight_v2(
    *,
    family_id: str,
    scope: RuntimeScopeV2,
    selected_document_ids: tuple[str, ...],
    current_documents: tuple[CurrentDocumentRefsV1, ...],
    stage_pins: dict[FormalStageV1, StagePinsV1],
    cached_receipts: tuple[StageReceiptV1, ...],
    failure_ledger: FailureLedgerV2,
) -> RuntimePreflightV2:
    """Declare the exact run budget and pin vector before execution starts."""

    _validate_generic_id(family_id, "preflight family ID")
    validate_failure_ledger_v2(failure_ledger)
    if failure_ledger.family_id != family_id:
        raise _error("preflight and failure ledger families differ")
    target_budget, hard_budget = _budget_for_scope(scope)
    provisional = RuntimePreflightV2(
        _PREFLIGHT_FORMAT_VERSION,
        CLAIM_BOUNDARY,
        family_id,
        scope,
        selected_document_ids,
        _document_manifest_ref(current_documents),
        _cache_manifest_ref(cached_receipts),
        _failure_ledger_ref(failure_ledger),
        _stage_revisions(stage_pins),
        target_budget,
        hard_budget,
        "",
    )
    result = replace(provisional, preflight_id=_preflight_id(provisional))
    return _validate_preflight(result)


def _validate_runtime_stage(value: Any) -> PlannedRuntimeStageV2:
    if type(value) is not PlannedRuntimeStageV2 or type(value.base_stage) is not PlannedStageV1:
        raise _error("planned runtime stage must retain its exact V2/V1 types")
    if (
        type(value.decision) is not CacheDecisionV1
        or type(value.lifecycle_action) is not LifecycleActionV2
        or type(value.algorithm_revision_key) is not str
        or _REVISION_KEY.fullmatch(value.algorithm_revision_key) is None
        or type(value.preflight_id) is not str
        or _PREFLIGHT_ID.fullmatch(value.preflight_id) is None
        or type(value.resolution_target_ids) is not tuple
        or any(type(item) is not str for item in value.resolution_target_ids)
        or tuple(sorted(set(value.resolution_target_ids))) != value.resolution_target_ids
    ):
        raise _error("planned runtime stage lifecycle shape drifted")
    return value


def _validate_stage_preflight_binding(
    stage: PlannedRuntimeStageV2, preflight: RuntimePreflightV2
) -> None:
    revision_by_stage = {
        item.stage: item.algorithm_revision_key for item in preflight.stage_revisions
    }
    if (
        stage.preflight_id != preflight.preflight_id
        or revision_by_stage.get(stage.stage) != stage.algorithm_revision_key
        or stage.document_id not in preflight.selected_document_ids
    ):
        raise _error("planned runtime stage drifted from its exact preflight pins/scope")


def _new_observation(
    *,
    ledger: FailureLedgerV2,
    stage: PlannedRuntimeStageV2,
    preflight: RuntimePreflightV2,
    kind: RuntimeObservationKindV2,
    taxonomy: FailureTaxonomyV2 | None,
    observed_runtime_ms: int,
    success_purpose: SuccessPurposeV2 | None = None,
    resolves_observation_ids: tuple[str, ...] = (),
    result_receipt_id: str | None = None,
) -> RuntimeObservationV2:
    provisional = RuntimeObservationV2(
        _OBSERVATION_FORMAT_VERSION,
        CLAIM_BOUNDARY,
        len(ledger.observations) + 1,
        ledger.head_observation_id,
        ledger.family_id,
        stage.document_id,
        stage.stage,
        stage.algorithm_revision_key,
        stage.expected_stage_key or "",
        preflight.preflight_id,
        preflight.scope,
        preflight.target_budget_ms,
        preflight.hard_budget_ms,
        kind,
        taxonomy,
        observed_runtime_ms,
        success_purpose,
        resolves_observation_ids,
        result_receipt_id,
        "",
    )
    return replace(provisional, observation_id=_observation_id(provisional))


def append_stage_failure_v2(
    failure_ledger: FailureLedgerV2,
    planned_stage: PlannedRuntimeStageV2,
    *,
    preflight: RuntimePreflightV2,
    taxonomy: FailureTaxonomyV2,
    observed_runtime_ms: int,
) -> FailureLedgerV2:
    """Append one classified failure; runtime classification is policy-derived."""

    ledger = validate_failure_ledger_v2(failure_ledger)
    stage = _validate_runtime_stage(planned_stage)
    flight = _validate_preflight(preflight)
    _validate_stage_preflight_binding(stage, flight)
    if ledger.family_id != flight.family_id:
        raise _error("failure append does not bind the current ledger/preflight")
    if stage.decision is not CacheDecisionV1.RECOMPUTE or stage.expected_stage_key is None:
        raise _error("failure observations may only append for a runnable stage")
    if type(taxonomy) is not FailureTaxonomyV2 or taxonomy not in _NON_RUNTIME_FAILURES:
        raise _error("failure taxonomy must be one closed non-runtime enum value")
    _validate_exact_int(observed_runtime_ms, "observed runtime")
    if observed_runtime_ms > flight.hard_budget_ms:
        kind = RuntimeObservationKindV2.HARD_BUDGET_BREACH
        selected_taxonomy = FailureTaxonomyV2.RUNTIME_HARD_BREACH
    elif observed_runtime_ms > flight.target_budget_ms:
        kind = RuntimeObservationKindV2.TARGET_BUDGET_BREACH
        selected_taxonomy = FailureTaxonomyV2.RUNTIME_TARGET_BREACH
    else:
        kind = RuntimeObservationKindV2.STAGE_FAILURE
        selected_taxonomy = taxonomy
    observation = _new_observation(
        ledger=ledger,
        stage=stage,
        preflight=flight,
        kind=kind,
        taxonomy=selected_taxonomy,
        observed_runtime_ms=observed_runtime_ms,
    )
    return _close_ledger(ledger, observation)


def build_targeted_stage_receipt_v2(
    planned_stage: PlannedRuntimeStageV2,
    *,
    page_count: int,
    output_sha256: str,
    output_size_bytes: int,
    outcome: StageOutcomeV1,
    coverage_bound: PageCoverageBoundV1 | None = None,
) -> StageReceiptV1:
    """Build a V1 receipt for a V2-forced targeted rerun."""

    stage = _validate_runtime_stage(planned_stage)
    if (
        stage.decision is not CacheDecisionV1.RECOMPUTE
        or stage.lifecycle_action
        not in {
            LifecycleActionV2.TARGETED_RETRY_REQUIRED,
            LifecycleActionV2.REVISION_PROBATION_REQUIRED,
            LifecycleActionV2.TARGETED_RETRY_AND_REVISION_PROBATION,
        }
    ):
        raise _error("targeted receipt requires one lifecycle-forced runnable stage")
    runnable = replace(stage.base_stage, decision=CacheDecisionV1.RECOMPUTE)
    return build_stage_receipt_v1(
        runnable,
        page_count=page_count,
        output_sha256=output_sha256,
        output_size_bytes=output_size_bytes,
        outcome=outcome,
        coverage_bound=coverage_bound,
    )


def append_targeted_success_v2(
    failure_ledger: FailureLedgerV2,
    planned_stage: PlannedRuntimeStageV2,
    *,
    preflight: RuntimePreflightV2,
    result_receipt: StageReceiptV1,
    observed_runtime_ms: int,
) -> FailureLedgerV2:
    """Append a fresh targeted success without erasing any historical counter."""

    ledger = validate_failure_ledger_v2(failure_ledger)
    stage = _validate_runtime_stage(planned_stage)
    flight = _validate_preflight(preflight)
    _validate_stage_preflight_binding(stage, flight)
    if flight.scope is not RuntimeScopeV2.TARGETED:
        raise _error("targeted success requires a predeclared TARGETED preflight")
    if ledger.family_id != flight.family_id:
        raise _error("targeted success does not bind the current ledger/preflight")
    if (
        stage.decision is not CacheDecisionV1.RECOMPUTE
        or stage.lifecycle_action
        not in {
            LifecycleActionV2.TARGETED_RETRY_REQUIRED,
            LifecycleActionV2.REVISION_PROBATION_REQUIRED,
            LifecycleActionV2.TARGETED_RETRY_AND_REVISION_PROBATION,
        }
        or not stage.resolution_target_ids
        or stage.expected_stage_key is None
    ):
        raise _error("targeted success requires an unresolved lifecycle target")
    _validate_exact_int(observed_runtime_ms, "observed runtime")
    if observed_runtime_ms > flight.target_budget_ms:
        raise _error("over-budget execution cannot be recorded as targeted success")
    if (
        type(result_receipt) is not StageReceiptV1
        or result_receipt.document_id != stage.document_id
        or result_receipt.stage is not stage.stage
        or result_receipt.stage_key != stage.expected_stage_key
        or result_receipt.dependencies != stage.expected_dependencies
        or type(result_receipt.receipt_id) is not str
        or _RECEIPT_ID.fullmatch(result_receipt.receipt_id) is None
    ):
        raise _error("targeted success receipt does not bind the exact planned stage")
    by_id = {item.observation_id: item for item in ledger.observations}
    targets = tuple(by_id[item] for item in stage.resolution_target_ids)
    has_current = any(
        item.algorithm_revision_key == stage.algorithm_revision_key for item in targets
    )
    has_prior = any(
        item.algorithm_revision_key != stage.algorithm_revision_key for item in targets
    )
    purpose = (
        SuccessPurposeV2.INCIDENT_AND_REVISION_PROBATION
        if has_current and has_prior
        else SuccessPurposeV2.INCIDENT_RESOLUTION
        if has_current
        else SuccessPurposeV2.REVISION_PROBATION
    )
    observation = _new_observation(
        ledger=ledger,
        stage=stage,
        preflight=flight,
        kind=RuntimeObservationKindV2.TARGETED_SUCCESS,
        taxonomy=None,
        observed_runtime_ms=observed_runtime_ms,
        success_purpose=purpose,
        resolves_observation_ids=stage.resolution_target_ids,
        result_receipt_id=result_receipt.receipt_id,
    )
    return _close_ledger(ledger, observation)


def _replace_runtime_decision(
    value: PlannedRuntimeStageV2,
    *,
    decision: CacheDecisionV1,
    action: LifecycleActionV2,
    targets: tuple[str, ...] = (),
) -> PlannedRuntimeStageV2:
    return replace(value, decision=decision, lifecycle_action=action, resolution_target_ids=targets)


def _review_action(
    observations: tuple[RuntimeObservationV2, ...],
) -> LifecycleActionV2 | None:
    if any(item.kind is RuntimeObservationKindV2.HARD_BUDGET_BREACH for item in observations):
        return LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_HARD_BUDGET
    target_breaches = tuple(
        item
        for item in observations
        if item.kind is RuntimeObservationKindV2.TARGET_BUDGET_BREACH
    )
    first_target_sequence = min(
        (item.sequence for item in target_breaches),
        default=None,
    )
    failed_profiled_followup = first_target_sequence is not None and any(
        item.sequence > first_target_sequence
        and item.kind
        in {
            RuntimeObservationKindV2.STAGE_FAILURE,
            RuntimeObservationKindV2.TARGET_BUDGET_BREACH,
        }
        for item in observations
    )
    if len(target_breaches) >= 2 or failed_profiled_followup:
        return LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_TARGET_BUDGET
    failures = Counter(
        item.taxonomy
        for item in observations
        if item.kind is RuntimeObservationKindV2.STAGE_FAILURE
    )
    if any(count >= 2 for count in failures.values()):
        return LifecycleActionV2.ALGORITHM_REVIEW_REQUIRED_REPEAT_FAILURE
    return None


def _expected_current_refs(
    current_documents: tuple[CurrentDocumentRefsV1, ...],
    cached_receipts: tuple[StageReceiptV1, ...],
    ledger: FailureLedgerV2,
) -> CallerCurrentRefsV2:
    return build_caller_current_refs_v2(
        current_documents=current_documents,
        cached_receipts=cached_receipts,
        failure_ledger=ledger,
    )


def plan_incremental_formal_runtime_v2(
    *,
    mode: PlanModeV1,
    current_documents: tuple[CurrentDocumentRefsV1, ...],
    stage_pins: dict[FormalStageV1, StagePinsV1],
    cached_receipts: tuple[StageReceiptV1, ...],
    family_id: str,
    failure_ledger: FailureLedgerV2,
    preflight: RuntimePreflightV2,
    dev_document_ids: tuple[str, ...] = (),
    caller_current_refs: CallerCurrentRefsV2 | None = None,
) -> IncrementalFormalRuntimePlanV2:
    """Plan V1's frontier under mandatory V2 ledger and preflight controls."""

    ledger = validate_failure_ledger_v2(failure_ledger)
    flight = _validate_preflight(preflight)
    _validate_generic_id(family_id, "caller-current family ID")
    if ledger.family_id != family_id or flight.family_id != family_id:
        raise _error("ledger/preflight family does not match the caller-current family")
    base = plan_incremental_formal_dag_v1(
        mode=mode,
        current_documents=current_documents,
        stage_pins=stage_pins,
        cached_receipts=cached_receipts,
        dev_document_ids=dev_document_ids,
        family_id=family_id,
        attempt_history=(),
    )
    if flight.selected_document_ids != base.selected_document_ids:
        raise _error("preflight selected documents differ from the exact DAG selection")
    if flight.scope in {RuntimeScopeV2.FOCUSED, RuntimeScopeV2.TARGETED}:
        if mode is not PlanModeV1.DEV_FAST:
            raise _error("focused/targeted execution requires DEV_FAST document isolation")
    elif mode is PlanModeV1.DEV_FAST:
        raise _error("FAMILY_140_COLD cannot run through DEV_FAST")
    expected_doc_ref = _document_manifest_ref(current_documents)
    expected_cache_ref = _cache_manifest_ref(cached_receipts)
    expected_ledger_ref = _failure_ledger_ref(ledger)
    expected_revisions = _stage_revisions(stage_pins)
    if (
        flight.document_manifest_ref != expected_doc_ref
        or flight.cache_manifest_ref != expected_cache_ref
        or flight.failure_ledger_ref != expected_ledger_ref
        or flight.stage_revisions != expected_revisions
    ):
        raise _error("runtime preflight is stale relative to current inputs or exact pins")

    expected_refs = _expected_current_refs(current_documents, cached_receipts, ledger)
    if caller_current_refs is None:
        current_refs_match = False
    else:
        supplied_refs = _validate_caller_current_refs(caller_current_refs)
        current_refs_match = supplied_refs == expected_refs

    revision_by_stage = {item.stage: item.algorithm_revision_key for item in expected_revisions}
    receipts_by_id = {item.receipt_id: item for item in cached_receipts}
    events_by_revision: dict[tuple[FormalStageV1, str], list[RuntimeObservationV2]] = defaultdict(list)
    events_by_doc_stage_revision: dict[
        tuple[str, FormalStageV1, str], list[RuntimeObservationV2]
    ] = defaultdict(list)
    incidents_by_doc_stage: dict[tuple[str, FormalStageV1], list[RuntimeObservationV2]] = (
        defaultdict(list)
    )
    for observation in ledger.observations:
        if observation.kind is not RuntimeObservationKindV2.TARGETED_SUCCESS:
            events_by_revision[(observation.stage, observation.algorithm_revision_key)].append(
                observation
            )
            events_by_doc_stage_revision[
                (
                    observation.document_id,
                    observation.stage,
                    observation.algorithm_revision_key,
                )
            ].append(observation)
            incidents_by_doc_stage[(observation.document_id, observation.stage)].append(
                observation
            )

    observation_by_id = {item.observation_id: item for item in ledger.observations}
    valid_successes: list[RuntimeObservationV2] = []
    for observation in ledger.observations:
        if observation.kind is not RuntimeObservationKindV2.TARGETED_SUCCESS:
            continue
        receipt = receipts_by_id.get(observation.result_receipt_id or "")
        if (
            receipt is not None
            and receipt.document_id == observation.document_id
            and receipt.stage is observation.stage
            and receipt.stage_key == observation.stage_key
        ):
            valid_successes.append(observation)
    valid_successes_by_doc_stage_revision: dict[
        tuple[str, FormalStageV1, str], list[RuntimeObservationV2]
    ] = defaultdict(list)
    for success in valid_successes:
        valid_successes_by_doc_stage_revision[
            (success.document_id, success.stage, success.algorithm_revision_key)
        ].append(success)
    resolved_incident_ids = {
        target_id
        for success in valid_successes
        for target_id in success.resolves_observation_ids
        if observation_by_id[target_id].algorithm_revision_key
        == success.algorithm_revision_key
    }

    pending_probation: dict[FormalStageV1, dict[str, RuntimeObservationV2]] = defaultdict(dict)
    current_ids = {item.document_id for item in current_documents}
    for (document_id, stage), incidents in incidents_by_doc_stage.items():
        if document_id not in current_ids:
            continue
        current_revision = revision_by_stage[stage]
        prior = tuple(
            item for item in incidents if item.algorithm_revision_key != current_revision
        )
        if not prior:
            continue
        probation_closed = any(
            any(
                observation_by_id[target_id].algorithm_revision_key
                != current_revision
                for target_id in success.resolves_observation_ids
            )
            for success in valid_successes_by_doc_stage_revision.get(
                (document_id, stage, current_revision), ()
            )
        )
        if not probation_closed:
            pending_probation[stage][document_id] = max(
                prior, key=lambda item: item.sequence
            )

    review_by_revision = {
        key: _review_action(tuple(observations))
        for key, observations in events_by_revision.items()
    }
    wrapped: list[PlannedRuntimeStageV2] = []
    for item in base.decisions:
        revision = revision_by_stage[item.stage]
        review = review_by_revision.get((item.stage, revision))
        result = PlannedRuntimeStageV2(
            item,
            item.decision,
            LifecycleActionV2.BASE_DAG_DECISION,
            revision,
            flight.preflight_id,
            (),
        )
        if item.decision is CacheDecisionV1.SKIPPED:
            wrapped.append(result)
            continue
        if review is not None:
            wrapped.append(
                _replace_runtime_decision(
                    result,
                    decision=CacheDecisionV1.BLOCKED,
                    action=review,
                )
            )
            continue

        current_incidents = tuple(
            event
            for event in events_by_doc_stage_revision.get(
                (item.document_id, item.stage, revision), ()
            )
            if event.kind
            in {
                RuntimeObservationKindV2.STAGE_FAILURE,
                RuntimeObservationKindV2.TARGET_BUDGET_BREACH,
            }
            and event.observation_id not in resolved_incident_ids
        )
        probation_for_stage = pending_probation.get(item.stage, {})
        probation_trigger = probation_for_stage.get(item.document_id)
        if probation_for_stage:
            if probation_trigger is None:
                wrapped.append(
                    _replace_runtime_decision(
                        result,
                        decision=CacheDecisionV1.BLOCKED,
                        action=LifecycleActionV2.REVISION_PROBATION_PENDING_ELSEWHERE,
                    )
                )
                continue
            targets = tuple(
                sorted(
                    {
                        *(event.observation_id for event in current_incidents),
                        probation_trigger.observation_id,
                    }
                )
            )
            if flight.scope is not RuntimeScopeV2.TARGETED or item.expected_stage_key is None:
                wrapped.append(
                    _replace_runtime_decision(
                        result,
                        decision=CacheDecisionV1.BLOCKED,
                        action=LifecycleActionV2.TARGETED_PREFLIGHT_REQUIRED,
                        targets=targets,
                    )
                )
                continue
            action = (
                LifecycleActionV2.TARGETED_RETRY_AND_REVISION_PROBATION
                if current_incidents
                else LifecycleActionV2.REVISION_PROBATION_REQUIRED
            )
            wrapped.append(
                _replace_runtime_decision(
                    result,
                    decision=CacheDecisionV1.RECOMPUTE,
                    action=action,
                    targets=targets,
                )
            )
            continue
        if current_incidents:
            targets = tuple(sorted(item.observation_id for item in current_incidents))
            if flight.scope is not RuntimeScopeV2.TARGETED or item.expected_stage_key is None:
                wrapped.append(
                    _replace_runtime_decision(
                        result,
                        decision=CacheDecisionV1.BLOCKED,
                        action=LifecycleActionV2.TARGETED_PREFLIGHT_REQUIRED,
                        targets=targets,
                    )
                )
            else:
                wrapped.append(
                    _replace_runtime_decision(
                        result,
                        decision=CacheDecisionV1.RECOMPUTE,
                        action=LifecycleActionV2.TARGETED_RETRY_REQUIRED,
                        targets=targets,
                    )
                )
            continue
        wrapped.append(result)

    # A lifecycle-controlled stage cannot be bypassed by cached descendants.
    by_doc_stage = {(item.document_id, item.stage): index for index, item in enumerate(wrapped)}
    controlled = tuple(
        item
        for item in wrapped
        if item.lifecycle_action is not LifecycleActionV2.BASE_DAG_DECISION
        and item.lifecycle_action is not LifecycleActionV2.UPSTREAM_LIFECYCLE_PENDING
    )
    for parent in controlled:
        descendants = stage_invalidation_closure_v1(
            (parent.stage,), rescue_possible=True, include_release_seal=True
        )
        for descendant in descendants:
            if descendant is parent.stage:
                continue
            index = by_doc_stage.get((parent.document_id, descendant))
            if index is None or wrapped[index].decision is CacheDecisionV1.SKIPPED:
                continue
            wrapped[index] = _replace_runtime_decision(
                wrapped[index],
                decision=CacheDecisionV1.BLOCKED,
                action=LifecycleActionV2.UPSTREAM_LIFECYCLE_PENDING,
            )

    active = tuple(item for item in wrapped if item.decision is not CacheDecisionV1.SKIPPED)
    execution_ready = bool(active) and all(
        item.decision is CacheDecisionV1.HIT for item in active
    )
    if mode is not PlanModeV1.RELEASE_SEAL:
        authority = ReleaseAuthorityV2.NOT_RELEASE_MODE
    elif caller_current_refs is None:
        authority = ReleaseAuthorityV2.NON_AUTHORITATIVE_MISSING_CALLER_CURRENT_REFS
    elif not current_refs_match:
        authority = ReleaseAuthorityV2.NON_AUTHORITATIVE_CALLER_CURRENT_REF_DRIFT
    elif not execution_ready:
        authority = ReleaseAuthorityV2.NON_AUTHORITATIVE_EXECUTION_INCOMPLETE
    else:
        authority = ReleaseAuthorityV2.CALLER_CURRENT_BOUND_RELEASE_CANDIDATE
    ready = execution_ready and (
        mode is not PlanModeV1.RELEASE_SEAL
        or authority is ReleaseAuthorityV2.CALLER_CURRENT_BOUND_RELEASE_CANDIDATE
    )
    return IncrementalFormalRuntimePlanV2(
        FORMAT_VERSION,
        mode,
        flight.scope,
        len(current_documents),
        base.selected_document_ids,
        tuple(wrapped),
        execution_ready,
        ready,
        authority,
        ledger.counters,
    )
