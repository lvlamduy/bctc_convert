"""Fail-closed item reconciliation for a visible direct-method LCTT block."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz.fuzz import partial_ratio, ratio

from bctc_ai.core.text import retrieval_key
from bctc_ai.mapping.lctt import CashFlowMethod
from bctc_ai.mapping.ordered_subgraph_v2 import (
    OrderedSubgraphV2Error,
    OrderedSubgraphV2Policy,
    SchemaProjectionV2,
    build_schema_projection_v2,
    load_ordered_subgraph_v2_policy_bytes,
)
from bctc_ai.schema.registry import SchemaItem

LCTT_POLICY_RELATIVE_PATH = Path("config/mapping/lctt-direct-ordered-subgraph-v2.yaml")
LCTT_SCHEMA_ITEM_COUNT = 110
LCTT_DIRECT_SCHEMA_ITEM_COUNT = 53
LCTT_INDIRECT_SCHEMA_ITEM_COUNT = 57
LCTT_VISIBLE_SOURCE_ROW_COUNT = 43
LCTT_TRAILING_AGGREGATE_IDS = (4109, 4110, 4111, 4112, 4114, 4116)
LCTT_DIRECT_AGGREGATE_IDS = (
    4109,
    4107,
    4108,
    4110,
    6034,
    5714,
    4111,
    4112,
    4114,
    4116,
)

_BUSINESS_RESOLUTION_IDS = {4140, 6034, 5714}
_BUSINESS_RESOLUTION_ROWS = {
    "page-0007:row-0024": 4140,
    "page-0007:row-0031": 6034,
    "page-0007:row-0032": 5714,
}
_BUSINESS_RESOLUTION_KEYS = {
    4140: "USER_Q018_CONTEXTUAL_WORDING_TO_4140",
    6034: "INVESTMENT_PROPERTY_NET_TO_6034",
    5714: "INVESTMENT_CONTRIBUTION_NET_TO_5714",
}
_BUSINESS_RESOLUTION_DECISION_BASES = {
    4140: "USER_AUTHORIZED_CONTEXTUAL_WORDING_MAPPING",
    6034: "APPROVED_BUSINESS_SCHEMA_MAPPING",
    5714: "APPROVED_BUSINESS_SCHEMA_MAPPING",
}
_NOT_OBSERVED_IDS = {4143, 4144, 4145, 4146, 4120, 4121, 4151, 4152, 4117, 6054}

_MAX_LABEL_LENGTH = 4096
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAPPING_INPUTS = (
    "LCTT_WORKBOOK_DISPLAY_ORDER",
    "LCTT_DIRECT_BRANCH_HIERARCHY",
    "CANONICAL_AND_STRUCTURAL_ALIASES",
    "SOURCE_VISIBLE_PPOCR_LABELS",
    "VISIBLE_DIRECT_METHOD_BINDING",
    "APPROVED_BUSINESS_SCHEMA_RESOLUTIONS",
)
_DUAL_MAPPING_INPUTS = _MAPPING_INPUTS + ("INDEPENDENT_SOURCE_PIXEL_SEMANTIC_LABELS",)


class LCTTItemMappingError(ValueError):
    """Raised when LCTT candidate evidence or reconciliation is malformed."""


class LCTTSchemaStatus(StrEnum):
    MAPPED_AUTOMATIC = "MAPPED_AUTOMATIC"
    LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC = "LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC"
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    SCHEMA_ITEM_NOT_APPLICABLE = "SCHEMA_ITEM_NOT_APPLICABLE"


class LCTTSourceRowStatus(StrEnum):
    MAPPED_AUTOMATIC = "MAPPED_AUTOMATIC"
    LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC = "LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC"
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    SOURCE_ONLY_PDF_ROW = "SOURCE_ONLY_PDF_ROW"


@dataclass(frozen=True)
class LCTTBusinessResolutionRule:
    key: str
    source_row_id: str
    visible_label_anchor: str
    minimum_anchor_similarity: float
    report_norm_id: int
    decision_basis: str


@dataclass(frozen=True)
class LCTTDirectMappingPolicy:
    source_path: Path
    core: OrderedSubgraphV2Policy
    applicable_branch: str
    schema_total: int
    applicable_branch_total: int
    non_applicable_branch_total: int
    visible_source_row_total: int
    minimum_independent_semantic_streams: int
    currently_available_independent_semantic_streams: int
    minimum_monotone_candidate_label_score: float
    minimum_cross_reader_label_similarity: float
    not_observed_report_norm_ids: tuple[int, ...]
    business_resolution_rules: tuple[LCTTBusinessResolutionRule, ...]
    policy_sha256: str


@dataclass(frozen=True)
class LCTTSourceVisibleRow:
    row_id: str
    order: int
    page_tag: str
    visible_label: str
    source_reader_id: str


@dataclass(frozen=True)
class LCTTSchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    cash_flow_branch: str
    status: str
    candidate_source_row_ids: tuple[str, ...]
    label_similarity: float | None
    independent_label_similarity: float | None
    cross_reader_label_similarity: float | None
    supporting_reader_ids: tuple[str, ...]
    label_conflict_key: str | None
    business_resolution_key: str | None
    reason: str


@dataclass(frozen=True)
class LCTTSourceDisposition:
    row_id: str
    order: int
    page_tag: str
    visible_label: str
    status: str
    candidate_report_norm_ids: tuple[int, ...]
    label_similarity: float
    independent_label_similarity: float | None
    cross_reader_label_similarity: float | None
    supporting_reader_ids: tuple[str, ...]
    label_conflict_key: str | None
    business_resolution_key: str | None
    reason: str


@dataclass(frozen=True)
class LCTTItemMappingResult:
    statement_type: str
    report_scope: str
    cash_flow_method: str
    status: str
    automatic_selection_allowed: bool
    independent_semantic_stream_count: int
    minimum_independent_semantic_streams: int
    schema_item_count: int
    schema_status_reconciled_count: int
    mapped_schema_count: int
    candidate_linked_schema_count: int
    label_conflict_schema_count: int
    ambiguous_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    candidate_linked_source_row_count: int
    label_conflict_source_row_count: int
    source_only_row_count: int
    schema_dispositions: tuple[LCTTSchemaDisposition, ...]
    source_dispositions: tuple[LCTTSourceDisposition, ...]
    schema_projection_sha256: str
    policy_sha256: str
    source_label_sha256: str
    independent_label_sha256: str | None
    mapping_inputs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _required_int(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LCTTItemMappingError(f"invalid LCTT policy integer: {name}")
    return value


def _required_score(payload: Mapping[str, Any], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise LCTTItemMappingError(f"invalid LCTT policy score: {name}")
    return float(value)


def load_lctt_direct_mapping_policy(path: Path) -> LCTTDirectMappingPolicy:
    """Parse the common v2 contract and candidate overlay from identical bytes."""

    resolved = path.resolve()
    try:
        source_bytes = resolved.read_bytes()
        core = load_ordered_subgraph_v2_policy_bytes(source_bytes, source_path=resolved)
        payload = yaml.safe_load(source_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError, OrderedSubgraphV2Error) as exc:
        raise LCTTItemMappingError(f"cannot load LCTT direct mapping policy: {path}") from exc
    if not isinstance(payload, Mapping):
        raise LCTTItemMappingError("LCTT direct mapping policy is not an object")
    raw = payload.get("candidate_reconciliation")
    if not isinstance(raw, Mapping):
        raise LCTTItemMappingError("LCTT candidate reconciliation policy is absent")
    raw_not_observed = raw.get("not_observed_report_norm_ids")
    raw_business_resolutions = raw.get("business_resolved_source_rows")
    if not isinstance(raw_not_observed, list) or not isinstance(raw_business_resolutions, list):
        raise LCTTItemMappingError("LCTT candidate disposition policy is malformed")
    not_observed = tuple(raw_not_observed)
    if any(isinstance(item, bool) or not isinstance(item, int) for item in not_observed):
        raise LCTTItemMappingError("LCTT not-observed IDs are invalid")
    business_resolutions = []
    for item in raw_business_resolutions:
        if not isinstance(item, Mapping) or set(item) != {
            "key",
            "source_row_id",
            "visible_label_anchor",
            "minimum_anchor_similarity",
            "report_norm_id",
            "decision_basis",
        }:
            raise LCTTItemMappingError("LCTT business-resolution rule is invalid")
        report_norm_id = item.get("report_norm_id")
        if (
            not isinstance(item.get("key"), str)
            or not item["key"]
            or not isinstance(item.get("source_row_id"), str)
            or not item["source_row_id"]
            or not isinstance(item.get("visible_label_anchor"), str)
            or not retrieval_key(item["visible_label_anchor"])
            or isinstance(report_norm_id, bool)
            or not isinstance(report_norm_id, int)
            or not isinstance(item.get("decision_basis"), str)
            or not item["decision_basis"]
        ):
            raise LCTTItemMappingError("LCTT business-resolution rule is invalid")
        business_resolutions.append(
            LCTTBusinessResolutionRule(
                key=item["key"],
                source_row_id=item["source_row_id"],
                visible_label_anchor=retrieval_key(item["visible_label_anchor"]),
                minimum_anchor_similarity=_required_score(item, "minimum_anchor_similarity"),
                report_norm_id=report_norm_id,
                decision_basis=item["decision_basis"],
            )
        )
    policy = LCTTDirectMappingPolicy(
        source_path=resolved,
        core=core,
        applicable_branch=str(raw.get("applicable_branch", "")),
        schema_total=_required_int(raw, "schema_total"),
        applicable_branch_total=_required_int(raw, "applicable_branch_total"),
        non_applicable_branch_total=_required_int(raw, "non_applicable_branch_total"),
        visible_source_row_total=_required_int(raw, "visible_source_row_total"),
        minimum_independent_semantic_streams=_required_int(
            raw, "minimum_independent_semantic_streams_for_automatic_selection"
        ),
        currently_available_independent_semantic_streams=_required_int(
            raw, "currently_available_independent_semantic_streams"
        ),
        minimum_monotone_candidate_label_score=_required_score(
            raw, "minimum_monotone_candidate_label_score"
        ),
        minimum_cross_reader_label_similarity=_required_score(
            raw, "minimum_cross_reader_label_similarity"
        ),
        not_observed_report_norm_ids=not_observed,
        business_resolution_rules=tuple(business_resolutions),
        policy_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )
    business_ids = {rule.report_norm_id for rule in policy.business_resolution_rules}
    business_rows = {
        rule.source_row_id: rule.report_norm_id for rule in policy.business_resolution_rules
    }
    business_keys = {rule.report_norm_id: rule.key for rule in policy.business_resolution_rules}
    business_decision_bases = {
        rule.report_norm_id: rule.decision_basis for rule in policy.business_resolution_rules
    }
    if (
        policy.applicable_branch != CashFlowMethod.DIRECT.value
        or policy.schema_total != LCTT_SCHEMA_ITEM_COUNT
        or policy.applicable_branch_total != LCTT_DIRECT_SCHEMA_ITEM_COUNT
        or policy.non_applicable_branch_total != LCTT_INDIRECT_SCHEMA_ITEM_COUNT
        or policy.visible_source_row_total != LCTT_VISIBLE_SOURCE_ROW_COUNT
        or policy.minimum_independent_semantic_streams < 2
        or policy.currently_available_independent_semantic_streams != 1
        or raw.get("label_similarity_algorithm") != "MAX_FULL_OR_PARTIAL_RATIO_AFTER_RETRIEVAL_KEY"
        or set(policy.not_observed_report_norm_ids) != _NOT_OBSERVED_IDS
        or business_ids != _BUSINESS_RESOLUTION_IDS
        or business_rows != _BUSINESS_RESOLUTION_ROWS
        or business_keys != _BUSINESS_RESOLUTION_KEYS
        or business_decision_bases != _BUSINESS_RESOLUTION_DECISION_BASES
        or len(policy.business_resolution_rules) != len(_BUSINESS_RESOLUTION_IDS)
        or business_ids.intersection(policy.not_observed_report_norm_ids)
        or policy.core.trailing_aggregate_ids != LCTT_TRAILING_AGGREGATE_IDS
    ):
        raise LCTTItemMappingError("LCTT candidate reconciliation identity drifted")
    return policy


def build_lctt_direct_schema_projection(schema: Sequence[SchemaItem]) -> SchemaProjectionV2:
    """Build the applicable 53-item direct branch without reading history or values."""

    direct = tuple(
        item
        for item in schema
        if item.statement_type == "LCTT" and item.cash_flow_branch == CashFlowMethod.DIRECT.value
    )
    try:
        projection = build_schema_projection_v2(direct, "LCTT")
    except OrderedSubgraphV2Error as exc:
        raise LCTTItemMappingError("cannot build LCTT direct schema projection") from exc
    if len(projection.nodes) != LCTT_DIRECT_SCHEMA_ITEM_COUNT:
        raise LCTTItemMappingError("LCTT direct projection must contain exactly 53 items")
    if tuple(node.display_order for node in projection.nodes) != tuple(range(57, 110)):
        raise LCTTItemMappingError("LCTT direct workbook order drifted")
    aggregates = tuple(
        node.report_norm_id for node in projection.nodes if node.child_report_norm_ids
    )
    if aggregates != LCTT_DIRECT_AGGREGATE_IDS:
        raise LCTTItemMappingError("LCTT direct hierarchy aggregate inventory drifted")
    return projection


def _field(value: object, name: str) -> object:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def adapt_lctt_logical_rows(
    logical_rows: Sequence[object], *, source_reader_id: str = "ppocrv6-word-box"
) -> tuple[LCTTSourceVisibleRow, ...]:
    """Read parser identity and visible labels only; cells remain outside mapping."""

    if isinstance(logical_rows, (str, bytes)) or not isinstance(logical_rows, Sequence):
        raise LCTTItemMappingError("LCTT logical rows must be a sequence")
    if not isinstance(source_reader_id, str) or not source_reader_id:
        raise LCTTItemMappingError("LCTT source reader identity is invalid")
    rows = []
    for order, raw in enumerate(logical_rows):
        row_id = _field(raw, "row_id")
        page_tag = _field(raw, "page_tag")
        reader_row = _field(raw, "row")
        label = _field(reader_row, "label") if reader_row is not None else _field(raw, "label")
        if (
            not isinstance(row_id, str)
            or not row_id
            or not isinstance(page_tag, str)
            or not page_tag
            or not isinstance(label, str)
            or not label.strip()
            or len(label) > _MAX_LABEL_LENGTH
        ):
            raise LCTTItemMappingError("LCTT parser row identity or visible label is invalid")
        rows.append(
            LCTTSourceVisibleRow(
                row_id=row_id,
                order=order,
                page_tag=page_tag,
                visible_label=label,
                source_reader_id=source_reader_id,
            )
        )
    if len(rows) != LCTT_VISIBLE_SOURCE_ROW_COUNT:
        raise LCTTItemMappingError("LCTT source must contain exactly 43 logical rows")
    if len({row.row_id for row in rows}) != len(rows):
        raise LCTTItemMappingError("LCTT source row IDs are not unique")
    return tuple(rows)


def adapt_lctt_independent_semantic_rows(
    semantic_rows: Sequence[object],
    *,
    source_rows: Sequence[LCTTSourceVisibleRow],
    source_reader_id: str,
) -> tuple[LCTTSourceVisibleRow, ...]:
    """Bind one reference-blind semantic proposal to every source row."""

    if isinstance(semantic_rows, (str, bytes)) or not isinstance(semantic_rows, Sequence):
        raise LCTTItemMappingError("LCTT independent semantic rows must be a sequence")
    if not isinstance(source_reader_id, str) or not source_reader_id:
        raise LCTTItemMappingError("LCTT independent reader identity is invalid")
    if {row.source_reader_id for row in source_rows} == {source_reader_id}:
        raise LCTTItemMappingError("LCTT semantic reader must be independent of the source reader")
    rows = []
    for order, raw in enumerate(semantic_rows):
        row_id = _field(raw, "row_id")
        page_tag = _field(raw, "page_tag")
        candidate_labels = tuple(
            value
            for value in (
                _field(raw, "proposal_text"),
                _field(raw, "visible_label"),
                _field(raw, "label"),
            )
            if isinstance(value, str) and value.strip()
        )
        if (
            not isinstance(row_id, str)
            or not row_id
            or not isinstance(page_tag, str)
            or not page_tag
            or not candidate_labels
            or len(set(candidate_labels)) != 1
            or len(candidate_labels[0]) > _MAX_LABEL_LENGTH
        ):
            raise LCTTItemMappingError("LCTT independent semantic row is invalid")
        rows.append(
            LCTTSourceVisibleRow(
                row_id=row_id,
                order=order,
                page_tag=page_tag,
                visible_label=candidate_labels[0],
                source_reader_id=source_reader_id,
            )
        )
    expected_identity = tuple((row.row_id, row.order, row.page_tag) for row in source_rows)
    actual_identity = tuple((row.row_id, row.order, row.page_tag) for row in rows)
    if actual_identity != expected_identity:
        raise LCTTItemMappingError(
            "LCTT independent semantic stream must cover the same ordered 43 rows"
        )
    return tuple(rows)


def _label_similarity(label: str, node: object) -> float:
    candidates = (_field(node, "canonical_name"), *_field(node, "structural_aliases"))
    label_key = retrieval_key(label)
    return max(
        max(
            ratio(label_key, retrieval_key(candidate)),
            partial_ratio(label_key, retrieval_key(candidate)),
        )
        / 100
        for candidate in candidates
        if isinstance(candidate, str) and retrieval_key(candidate)
    )


def _cross_reader_similarity(left: str, right: str) -> float:
    return ratio(retrieval_key(left), retrieval_key(right)) / 100


def _anchor_similarity(label: str, anchor: str) -> float:
    return partial_ratio(retrieval_key(label), anchor) / 100


def _identify_business_resolutions(
    rows: tuple[LCTTSourceVisibleRow, ...], policy: LCTTDirectMappingPolicy
) -> dict[int, tuple[LCTTBusinessResolutionRule, LCTTSourceVisibleRow, float]]:
    by_row_id = {row.row_id: row for row in rows}
    selected = {}
    for rule in policy.business_resolution_rules:
        row = by_row_id.get(rule.source_row_id)
        if row is None:
            raise LCTTItemMappingError(
                f"LCTT business-resolution row {rule.source_row_id} is absent"
            )
        similarity = _anchor_similarity(row.visible_label, rule.visible_label_anchor)
        if similarity < rule.minimum_anchor_similarity:
            raise LCTTItemMappingError(
                f"LCTT business-resolution row {rule.source_row_id} label drifted"
            )
        selected[rule.report_norm_id] = (rule, row, similarity)
    if set(selected) != _BUSINESS_RESOLUTION_IDS:
        raise LCTTItemMappingError("LCTT business-resolution ID set drifted")
    return selected


def _source_label_digest(rows: Sequence[LCTTSourceVisibleRow]) -> str:
    payload = [
        {
            "row_id": row.row_id,
            "order": row.order,
            "page_tag": row.page_tag,
            "visible_label": row.visible_label,
            "source_reader_id": row.source_reader_id,
        }
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def reconcile_lctt_direct_items(
    logical_rows: Sequence[object],
    *,
    schema: Sequence[SchemaItem],
    policy: LCTTDirectMappingPolicy,
    report_scope: str,
    cash_flow_method: CashFlowMethod | str,
    source_reader_id: str = "ppocrv6-word-box",
    independent_semantic_rows: Sequence[object] | None = None,
    independent_source_reader_id: str | None = None,
) -> LCTTItemMappingResult:
    """Reconcile all 110 items using dual readers plus approved business resolutions."""

    method = CashFlowMethod(str(cash_flow_method))
    if method is not CashFlowMethod.DIRECT:
        raise LCTTItemMappingError("LCTT direct reconciliation requires visible DIRECT method")
    scope = str(report_scope).upper()
    if scope not in {"CONSOLIDATED", "SEPARATE"}:
        raise LCTTItemMappingError("LCTT report scope must be visibly resolved")
    rows = adapt_lctt_logical_rows(logical_rows, source_reader_id=source_reader_id)
    if independent_semantic_rows is None:
        if independent_source_reader_id is not None:
            raise LCTTItemMappingError("LCTT independent reader has no semantic rows")
        independent_rows: tuple[LCTTSourceVisibleRow, ...] = ()
    else:
        if independent_source_reader_id is None:
            raise LCTTItemMappingError("LCTT independent semantic rows have no reader identity")
        independent_rows = adapt_lctt_independent_semantic_rows(
            independent_semantic_rows,
            source_rows=rows,
            source_reader_id=independent_source_reader_id,
        )
    independent_by_row = {row.row_id: row for row in independent_rows}
    projection = build_lctt_direct_schema_projection(schema)
    all_lctt = tuple(
        sorted(
            (item for item in schema if item.statement_type == "LCTT"),
            key=lambda item: item.display_order,
        )
    )
    if len(all_lctt) != LCTT_SCHEMA_ITEM_COUNT:
        raise LCTTItemMappingError("LCTT schema denominator must be exactly 110")
    direct_by_id = projection.by_id()
    if any(
        report_norm_id not in direct_by_id for report_norm_id in policy.not_observed_report_norm_ids
    ):
        raise LCTTItemMappingError("LCTT not-observed policy references a non-direct item")
    business_resolutions = _identify_business_resolutions(rows, policy)
    if any(report_norm_id not in direct_by_id for report_norm_id in business_resolutions):
        raise LCTTItemMappingError("LCTT business-resolution policy references a non-direct item")
    business_by_row = {
        row.row_id: (report_norm_id, rule, similarity)
        for report_norm_id, (rule, row, similarity) in business_resolutions.items()
    }
    excluded_direct_ids = {
        *policy.not_observed_report_norm_ids,
        *business_resolutions,
    }
    candidate_nodes = tuple(
        node for node in projection.nodes if node.report_norm_id not in excluded_direct_ids
    )
    candidate_rows = tuple(row for row in rows if row.row_id not in business_by_row)
    if len(candidate_nodes) != 40 or len(candidate_rows) != 40:
        raise LCTTItemMappingError("LCTT monotone candidate denominator does not reconcile to 40")

    candidate_by_schema: dict[
        int,
        tuple[
            LCTTSourceVisibleRow,
            float,
            LCTTSourceVisibleRow | None,
            float | None,
            float | None,
            bool,
        ],
    ] = {}
    candidate_by_row: dict[
        str,
        tuple[
            int,
            float,
            LCTTSourceVisibleRow | None,
            float | None,
            float | None,
            bool,
        ],
    ] = {}
    for row, node in zip(candidate_rows, candidate_nodes, strict=True):
        similarity = _label_similarity(row.visible_label, node)
        if similarity < policy.minimum_monotone_candidate_label_score:
            raise LCTTItemMappingError(
                f"LCTT monotone candidate {row.row_id}->{node.report_norm_id} is unsupported"
            )
        independent_row = independent_by_row.get(row.row_id)
        independent_similarity = (
            _label_similarity(independent_row.visible_label, node)
            if independent_row is not None
            else None
        )
        cross_reader_similarity = (
            _cross_reader_similarity(row.visible_label, independent_row.visible_label)
            if independent_row is not None
            else None
        )
        automatic = bool(
            independent_similarity is not None
            and cross_reader_similarity is not None
            and min(similarity, independent_similarity) >= policy.core.minimum_strong_label_score
            and cross_reader_similarity >= policy.minimum_cross_reader_label_similarity
        )
        evidence = (
            row,
            similarity,
            independent_row,
            independent_similarity,
            cross_reader_similarity,
            automatic,
        )
        candidate_by_schema[node.report_norm_id] = evidence
        candidate_by_row[row.row_id] = (node.report_norm_id, *evidence[1:])

    independently_mapped_count = sum(evidence[-1] for evidence in candidate_by_schema.values())
    mapped_count = len(business_resolutions) + independently_mapped_count
    candidate_count = len(candidate_by_schema) - independently_mapped_count
    schema_dispositions = []
    for item in all_lctt:
        independent_similarity: float | None = None
        cross_reader_similarity: float | None = None
        supporting_reader_ids: tuple[str, ...] = ()
        label_conflict_key: str | None = None
        business_resolution_key: str | None = None
        if item.cash_flow_branch == CashFlowMethod.INDIRECT.value:
            status = LCTTSchemaStatus.SCHEMA_ITEM_NOT_APPLICABLE
            candidate_rows_for_item: tuple[str, ...] = ()
            similarity = None
            reason = "visible statement method is DIRECT; INDIRECT branch is not applicable"
        elif item.schema_id in policy.not_observed_report_norm_ids:
            status = LCTTSchemaStatus.NOT_OBSERVED_IN_THIS_PDF
            candidate_rows_for_item = ()
            similarity = None
            reason = "complete visible DIRECT row denominator contains no separate matching row"
        elif item.schema_id in business_resolutions:
            rule, source_row, similarity = business_resolutions[item.schema_id]
            status = LCTTSchemaStatus.MAPPED_AUTOMATIC
            candidate_rows_for_item = (source_row.row_id,)
            supporting_reader_ids = (source_row.source_reader_id,)
            business_resolution_key = rule.key
            reason = (
                f"{rule.decision_basis} resolution {rule.key} binds the exact visible "
                f"source row to ReportNormId {item.schema_id}"
            )
        else:
            (
                source_row,
                similarity,
                independent_row,
                independent_similarity,
                cross_reader_similarity,
                automatic,
            ) = candidate_by_schema[item.schema_id]
            candidate_rows_for_item = (source_row.row_id,)
            if automatic:
                status = LCTTSchemaStatus.MAPPED_AUTOMATIC
                if independent_row is None:
                    raise LCTTItemMappingError("LCTT automatic mapping lost independent evidence")
                supporting_reader_ids = (
                    source_row.source_reader_id,
                    independent_row.source_reader_id,
                )
                reason = (
                    "one-to-one monotone DIRECT-branch mapping is independently corroborated "
                    "by two source-pixel semantic readers"
                )
            else:
                status = LCTTSchemaStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
                supporting_reader_ids = (source_row.source_reader_id,)
                reason = (
                    "one-to-one monotone DIRECT-branch candidate did not satisfy both "
                    "independent semantic promotion gates"
                )
        schema_dispositions.append(
            LCTTSchemaDisposition(
                report_norm_id=item.schema_id,
                display_order=item.display_order,
                canonical_name=item.canonical_name,
                cash_flow_branch=str(item.cash_flow_branch),
                status=status.value,
                candidate_source_row_ids=candidate_rows_for_item,
                label_similarity=round(similarity, 6) if similarity is not None else None,
                independent_label_similarity=(
                    round(independent_similarity, 6) if independent_similarity is not None else None
                ),
                cross_reader_label_similarity=(
                    round(cross_reader_similarity, 6)
                    if cross_reader_similarity is not None
                    else None
                ),
                supporting_reader_ids=supporting_reader_ids,
                label_conflict_key=label_conflict_key,
                business_resolution_key=business_resolution_key,
                reason=reason,
            )
        )
    source_dispositions = []
    for row in rows:
        independent_similarity = None
        cross_reader_similarity = None
        supporting_reader_ids = ()
        label_conflict_key = None
        business_resolution_key = None
        if row.row_id in business_by_row:
            report_norm_id, rule, similarity = business_by_row[row.row_id]
            status = LCTTSourceRowStatus.MAPPED_AUTOMATIC
            candidate_ids = (report_norm_id,)
            supporting_reader_ids = (row.source_reader_id,)
            business_resolution_key = rule.key
            reason = (
                f"{rule.decision_basis} resolution {rule.key} binds this exact visible "
                f"row to ReportNormId {report_norm_id}"
            )
        else:
            (
                report_norm_id,
                similarity,
                independent_row,
                independent_similarity,
                cross_reader_similarity,
                automatic,
            ) = candidate_by_row[row.row_id]
            candidate_ids = (report_norm_id,)
            if automatic:
                status = LCTTSourceRowStatus.MAPPED_AUTOMATIC
                if independent_row is None:
                    raise LCTTItemMappingError(
                        "LCTT automatic source link lost independent evidence"
                    )
                supporting_reader_ids = (
                    row.source_reader_id,
                    independent_row.source_reader_id,
                )
                reason = "two independent semantic labels corroborate the monotone schema link"
            else:
                status = LCTTSourceRowStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
                supporting_reader_ids = (row.source_reader_id,)
                reason = "the monotone candidate did not satisfy both independent promotion gates"
        source_dispositions.append(
            LCTTSourceDisposition(
                row_id=row.row_id,
                order=row.order,
                page_tag=row.page_tag,
                visible_label=row.visible_label,
                status=status.value,
                candidate_report_norm_ids=candidate_ids,
                label_similarity=round(similarity, 6),
                independent_label_similarity=(
                    round(independent_similarity, 6) if independent_similarity is not None else None
                ),
                cross_reader_label_similarity=(
                    round(cross_reader_similarity, 6)
                    if cross_reader_similarity is not None
                    else None
                ),
                supporting_reader_ids=supporting_reader_ids,
                label_conflict_key=label_conflict_key,
                business_resolution_key=business_resolution_key,
                reason=reason,
            )
        )
    automatic_selection_allowed = mapped_count > 0
    semantic_stream_count = 1 + bool(independent_rows)
    source_mapping_complete = candidate_count == 0 and mapped_count == LCTT_VISIBLE_SOURCE_ROW_COUNT
    result = LCTTItemMappingResult(
        statement_type="LCTT",
        report_scope=scope,
        cash_flow_method=method.value,
        status=(
            "SOURCE_MAPPING_COMPLETE_NUMERIC_NOT_FULLY_VERIFIED"
            if source_mapping_complete
            else "PARTIAL_AUTOMATIC_MAPPING_WITH_UNRESOLVED_ITEMS"
        ),
        automatic_selection_allowed=automatic_selection_allowed,
        independent_semantic_stream_count=semantic_stream_count,
        minimum_independent_semantic_streams=policy.minimum_independent_semantic_streams,
        schema_item_count=LCTT_SCHEMA_ITEM_COUNT,
        schema_status_reconciled_count=LCTT_SCHEMA_ITEM_COUNT,
        mapped_schema_count=mapped_count,
        candidate_linked_schema_count=candidate_count,
        label_conflict_schema_count=0,
        ambiguous_schema_count=0,
        not_observed_schema_count=len(_NOT_OBSERVED_IDS),
        not_applicable_schema_count=57,
        fully_verified_schema_count=0,
        source_row_count=len(rows),
        mapped_source_row_count=mapped_count,
        candidate_linked_source_row_count=candidate_count,
        label_conflict_source_row_count=0,
        source_only_row_count=0,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        schema_projection_sha256=projection.projection_sha256,
        policy_sha256=policy.policy_sha256,
        source_label_sha256=_source_label_digest(rows),
        independent_label_sha256=(
            _source_label_digest(independent_rows) if independent_rows else None
        ),
        mapping_inputs=_DUAL_MAPPING_INPUTS if independent_rows else _MAPPING_INPUTS,
        reason=(
            "all 43 visible DIRECT rows are mapped; three use approved business-schema "
            "resolutions and 40 are independently corroborated; numeric cells remain "
            "not fully verified"
            if source_mapping_complete
            else f"three approved business-schema mappings are fixed; {candidate_count} "
            "remaining monotone candidates await an independent semantic stream"
        ),
    )
    return validate_lctt_item_mapping_result(result)


def validate_lctt_item_mapping_result(result: LCTTItemMappingResult) -> LCTTItemMappingResult:
    """Validate exact coverage, cross-links, and both mapping-authority paths."""

    has_independent_stream = result.independent_semantic_stream_count >= 2
    source_mapping_complete = (
        result.mapped_source_row_count == LCTT_VISIBLE_SOURCE_ROW_COUNT
        and result.candidate_linked_source_row_count == 0
    )
    if (
        result.statement_type != "LCTT"
        or result.status
        != (
            "SOURCE_MAPPING_COMPLETE_NUMERIC_NOT_FULLY_VERIFIED"
            if source_mapping_complete
            else "PARTIAL_AUTOMATIC_MAPPING_WITH_UNRESOLVED_ITEMS"
        )
        or not result.automatic_selection_allowed
        or result.independent_semantic_stream_count not in {1, 2}
        or (
            (result.mapped_schema_count, result.candidate_linked_schema_count)
            != ((43, 0) if has_independent_stream else (3, 40))
        )
        or result.mapped_schema_count != result.mapped_source_row_count
        or result.candidate_linked_schema_count != result.candidate_linked_source_row_count
        or result.label_conflict_schema_count != 0
        or result.label_conflict_source_row_count != 0
        or result.ambiguous_schema_count != 0
        or result.not_observed_schema_count != len(_NOT_OBSERVED_IDS)
        or result.not_applicable_schema_count != LCTT_INDIRECT_SCHEMA_ITEM_COUNT
        or result.source_only_row_count != 0
        or result.schema_item_count != LCTT_SCHEMA_ITEM_COUNT
        or result.schema_status_reconciled_count != LCTT_SCHEMA_ITEM_COUNT
        or result.fully_verified_schema_count != 0
        or result.source_row_count != LCTT_VISIBLE_SOURCE_ROW_COUNT
        or result.mapping_inputs
        != (_DUAL_MAPPING_INPUTS if has_independent_stream else _MAPPING_INPUTS)
        or (has_independent_stream and result.independent_label_sha256 is None)
        or (not has_independent_stream and result.independent_label_sha256 is not None)
        or _SHA256.fullmatch(result.schema_projection_sha256) is None
        or _SHA256.fullmatch(result.policy_sha256) is None
        or _SHA256.fullmatch(result.source_label_sha256) is None
        or (
            result.independent_label_sha256 is not None
            and _SHA256.fullmatch(result.independent_label_sha256) is None
        )
    ):
        raise LCTTItemMappingError("LCTT candidate reconciliation identity is invalid")
    schema = result.schema_dispositions
    source = result.source_dispositions
    schema_ids = {item.report_norm_id for item in schema}
    source_ids = {item.row_id for item in source}
    if (
        len(schema) != LCTT_SCHEMA_ITEM_COUNT
        or len(schema_ids) != len(schema)
        or [item.display_order for item in schema] != list(range(LCTT_SCHEMA_ITEM_COUNT))
        or len(source) != LCTT_VISIBLE_SOURCE_ROW_COUNT
        or len(source_ids) != len(source)
        or [item.order for item in source] != list(range(LCTT_VISIBLE_SOURCE_ROW_COUNT))
    ):
        raise LCTTItemMappingError("LCTT candidate reconciliation coverage is incomplete")
    expected_schema_counts = {
        LCTTSchemaStatus.MAPPED_AUTOMATIC.value: result.mapped_schema_count,
        LCTTSchemaStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value: result.candidate_linked_schema_count,
        LCTTSchemaStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value: 0,
        LCTTSchemaStatus.AMBIGUOUS_MAPPING.value: result.ambiguous_schema_count,
        LCTTSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value: result.not_observed_schema_count,
        LCTTSchemaStatus.SCHEMA_ITEM_NOT_APPLICABLE.value: result.not_applicable_schema_count,
    }
    if (
        any(
            sum(item.status == status for item in schema) != count
            for status, count in expected_schema_counts.items()
        )
        or sum(expected_schema_counts.values()) != LCTT_SCHEMA_ITEM_COUNT
    ):
        raise LCTTItemMappingError("LCTT schema reconciliation counts drifted")
    if (
        sum(item.status == LCTTSourceRowStatus.MAPPED_AUTOMATIC.value for item in source)
        != result.mapped_source_row_count
        or sum(
            item.status == LCTTSourceRowStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value
            for item in source
        )
        != result.candidate_linked_source_row_count
        or sum(
            item.status == LCTTSourceRowStatus.LABEL_CONFLICT_CANDIDATE_NOT_AUTOMATIC.value
            for item in source
        )
        != result.label_conflict_source_row_count
        or sum(item.status == LCTTSourceRowStatus.SOURCE_ONLY_PDF_ROW.value for item in source)
        != result.source_only_row_count
        or result.mapped_source_row_count
        + result.candidate_linked_source_row_count
        + result.source_only_row_count
        != LCTT_VISIBLE_SOURCE_ROW_COUNT
    ):
        raise LCTTItemMappingError("LCTT source reconciliation counts drifted")
    source_by_id = {item.row_id: item for item in source}
    schema_by_id = {item.report_norm_id: item for item in schema}
    if {
        item.report_norm_id
        for item in schema
        if item.status == LCTTSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
    } != _NOT_OBSERVED_IDS:
        raise LCTTItemMappingError("LCTT exact not-observed set drifted")
    for item in schema:
        if item.status == LCTTSchemaStatus.MAPPED_AUTOMATIC.value:
            if item.business_resolution_key is not None:
                if item.report_norm_id not in _BUSINESS_RESOLUTION_IDS:
                    raise LCTTItemMappingError(
                        "LCTT business-resolved schema ID is not policy-approved"
                    )
                expected_row_id = next(
                    row_id
                    for row_id, report_norm_id in _BUSINESS_RESOLUTION_ROWS.items()
                    if report_norm_id == item.report_norm_id
                )
                if (
                    item.candidate_source_row_ids != (expected_row_id,)
                    or item.business_resolution_key
                    != _BUSINESS_RESOLUTION_KEYS[item.report_norm_id]
                    or item.label_similarity is None
                    or item.independent_label_similarity is not None
                    or item.cross_reader_label_similarity is not None
                    or len(item.supporting_reader_ids) != 1
                    or item.label_conflict_key is not None
                ):
                    raise LCTTItemMappingError(
                        "LCTT business-resolved schema mapping lacks exact policy evidence"
                    )
            elif (
                item.label_similarity is None
                or item.independent_label_similarity is None
                or item.cross_reader_label_similarity is None
                or len(item.supporting_reader_ids) != 2
                or len(set(item.supporting_reader_ids)) != 2
                or item.label_conflict_key is not None
            ):
                raise LCTTItemMappingError("LCTT automatic schema mapping lacks dual evidence")
        elif item.business_resolution_key is not None:
            raise LCTTItemMappingError("LCTT non-mapped schema item carries business authority")
        if any(row_id not in source_by_id for row_id in item.candidate_source_row_ids):
            raise LCTTItemMappingError("LCTT schema candidate references an unknown source row")
        for row_id in item.candidate_source_row_ids:
            if item.report_norm_id not in source_by_id[row_id].candidate_report_norm_ids:
                raise LCTTItemMappingError(
                    "LCTT schema/source candidate cross-link is inconsistent"
                )
    for item in source:
        if item.status == LCTTSourceRowStatus.MAPPED_AUTOMATIC.value:
            if item.business_resolution_key is not None:
                if (
                    _BUSINESS_RESOLUTION_ROWS.get(item.row_id) not in item.candidate_report_norm_ids
                    or len(item.candidate_report_norm_ids) != 1
                    or item.business_resolution_key
                    != _BUSINESS_RESOLUTION_KEYS[item.candidate_report_norm_ids[0]]
                    or item.independent_label_similarity is not None
                    or item.cross_reader_label_similarity is not None
                    or len(item.supporting_reader_ids) != 1
                    or item.label_conflict_key is not None
                ):
                    raise LCTTItemMappingError(
                        "LCTT business-resolved source mapping lacks exact policy evidence"
                    )
            elif (
                item.independent_label_similarity is None
                or item.cross_reader_label_similarity is None
                or len(item.supporting_reader_ids) != 2
                or len(set(item.supporting_reader_ids)) != 2
                or item.label_conflict_key is not None
            ):
                raise LCTTItemMappingError("LCTT automatic source mapping lacks dual evidence")
        elif item.business_resolution_key is not None:
            raise LCTTItemMappingError("LCTT non-mapped source row carries business authority")
        if any(
            report_norm_id not in schema_by_id for report_norm_id in item.candidate_report_norm_ids
        ):
            raise LCTTItemMappingError("LCTT source candidate references an unknown schema item")
    return result


__all__ = [
    "LCTTBusinessResolutionRule",
    "LCTTDirectMappingPolicy",
    "LCTTItemMappingError",
    "LCTTItemMappingResult",
    "LCTTSchemaDisposition",
    "LCTTSchemaStatus",
    "LCTTSourceDisposition",
    "LCTTSourceRowStatus",
    "LCTTSourceVisibleRow",
    "LCTT_DIRECT_SCHEMA_ITEM_COUNT",
    "LCTT_DIRECT_AGGREGATE_IDS",
    "LCTT_INDIRECT_SCHEMA_ITEM_COUNT",
    "LCTT_POLICY_RELATIVE_PATH",
    "LCTT_SCHEMA_ITEM_COUNT",
    "LCTT_TRAILING_AGGREGATE_IDS",
    "LCTT_VISIBLE_SOURCE_ROW_COUNT",
    "adapt_lctt_independent_semantic_rows",
    "adapt_lctt_logical_rows",
    "build_lctt_direct_schema_projection",
    "load_lctt_direct_mapping_policy",
    "reconcile_lctt_direct_items",
    "validate_lctt_item_mapping_result",
]
