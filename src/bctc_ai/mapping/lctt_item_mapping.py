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
from rapidfuzz.fuzz import ratio

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
LCTT_SCHEMA_ITEM_COUNT = 107
LCTT_DIRECT_SCHEMA_ITEM_COUNT = 50
LCTT_INDIRECT_SCHEMA_ITEM_COUNT = 57
LCTT_VISIBLE_SOURCE_ROW_COUNT = 43
LCTT_TRAILING_AGGREGATE_IDS = (4109, 4110, 4111, 4112, 4114, 4116)

_MAX_LABEL_LENGTH = 4096
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAPPING_INPUTS = (
    "LCTT_WORKBOOK_DISPLAY_ORDER",
    "LCTT_DIRECT_BRANCH_HIERARCHY",
    "CANONICAL_AND_STRUCTURAL_ALIASES",
    "SOURCE_VISIBLE_PPOCR_LABELS",
    "VISIBLE_DIRECT_METHOD_BINDING",
)


class LCTTItemMappingError(ValueError):
    """Raised when LCTT candidate evidence or reconciliation is malformed."""


class LCTTSchemaStatus(StrEnum):
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    SCHEMA_ITEM_NOT_APPLICABLE = "SCHEMA_ITEM_NOT_APPLICABLE"


class LCTTSourceRowStatus(StrEnum):
    CANDIDATE_MAPPING_NOT_AUTOMATIC = "CANDIDATE_MAPPING_NOT_AUTOMATIC"
    SOURCE_ONLY_PDF_ROW = "SOURCE_ONLY_PDF_ROW"


@dataclass(frozen=True)
class LCTTCompositeRule:
    key: str
    visible_label_anchor: str
    minimum_anchor_similarity: float
    candidate_report_norm_ids: tuple[int, ...]


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
    minimum_composite_anchor_runner_up_margin: float
    not_observed_report_norm_ids: tuple[int, ...]
    composite_rules: tuple[LCTTCompositeRule, ...]
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
    ambiguous_schema_count: int
    not_observed_schema_count: int
    not_applicable_schema_count: int
    fully_verified_schema_count: int
    source_row_count: int
    candidate_linked_source_row_count: int
    source_only_row_count: int
    schema_dispositions: tuple[LCTTSchemaDisposition, ...]
    source_dispositions: tuple[LCTTSourceDisposition, ...]
    schema_projection_sha256: str
    policy_sha256: str
    source_label_sha256: str
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
    raw_composites = raw.get("composite_source_rows")
    if not isinstance(raw_not_observed, list) or not isinstance(raw_composites, list):
        raise LCTTItemMappingError("LCTT candidate disposition policy is malformed")
    not_observed = tuple(raw_not_observed)
    if any(isinstance(item, bool) or not isinstance(item, int) for item in not_observed):
        raise LCTTItemMappingError("LCTT not-observed IDs are invalid")
    composites = []
    for item in raw_composites:
        if not isinstance(item, Mapping) or set(item) != {
            "key",
            "visible_label_anchor",
            "minimum_anchor_similarity",
            "candidate_report_norm_ids",
        }:
            raise LCTTItemMappingError("LCTT composite source rule is invalid")
        candidate_ids = item.get("candidate_report_norm_ids")
        if (
            not isinstance(item.get("key"), str)
            or not item["key"]
            or not isinstance(item.get("visible_label_anchor"), str)
            or not retrieval_key(item["visible_label_anchor"])
            or not isinstance(candidate_ids, list)
            or len(candidate_ids) < 2
            or any(isinstance(value, bool) or not isinstance(value, int) for value in candidate_ids)
        ):
            raise LCTTItemMappingError("LCTT composite source rule is invalid")
        composites.append(
            LCTTCompositeRule(
                key=item["key"],
                visible_label_anchor=retrieval_key(item["visible_label_anchor"]),
                minimum_anchor_similarity=_required_score(item, "minimum_anchor_similarity"),
                candidate_report_norm_ids=tuple(candidate_ids),
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
        minimum_composite_anchor_runner_up_margin=_required_score(
            raw, "minimum_composite_anchor_runner_up_margin"
        ),
        not_observed_report_norm_ids=not_observed,
        composite_rules=tuple(composites),
        policy_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )
    composite_ids = tuple(
        report_norm_id
        for rule in policy.composite_rules
        for report_norm_id in rule.candidate_report_norm_ids
    )
    if (
        policy.applicable_branch != CashFlowMethod.DIRECT.value
        or policy.schema_total != LCTT_SCHEMA_ITEM_COUNT
        or policy.applicable_branch_total != LCTT_DIRECT_SCHEMA_ITEM_COUNT
        or policy.non_applicable_branch_total != LCTT_INDIRECT_SCHEMA_ITEM_COUNT
        or policy.visible_source_row_total != LCTT_VISIBLE_SOURCE_ROW_COUNT
        or policy.minimum_independent_semantic_streams < 2
        or policy.currently_available_independent_semantic_streams != 1
        or len(set(policy.not_observed_report_norm_ids)) != 4
        or len(composite_ids) != 5
        or len(set(composite_ids)) != 5
        or set(composite_ids).intersection(policy.not_observed_report_norm_ids)
        or policy.core.trailing_aggregate_ids != LCTT_TRAILING_AGGREGATE_IDS
    ):
        raise LCTTItemMappingError("LCTT candidate reconciliation identity drifted")
    return policy


def build_lctt_direct_schema_projection(schema: Sequence[SchemaItem]) -> SchemaProjectionV2:
    """Build the applicable 50-item direct branch without reading history or values."""

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
        raise LCTTItemMappingError("LCTT direct projection must contain exactly 50 items")
    if tuple(node.display_order for node in projection.nodes) != tuple(range(57, 107)):
        raise LCTTItemMappingError("LCTT direct workbook order drifted")
    aggregates = tuple(
        node.report_norm_id for node in projection.nodes if node.child_report_norm_ids
    )
    if aggregates != LCTT_TRAILING_AGGREGATE_IDS:
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


def _label_similarity(label: str, node: object) -> float:
    candidates = (_field(node, "canonical_name"), *_field(node, "structural_aliases"))
    label_key = retrieval_key(label)
    return max(
        ratio(label_key, retrieval_key(candidate)) / 100
        for candidate in candidates
        if isinstance(candidate, str) and retrieval_key(candidate)
    )


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


def _identify_composites(
    rows: tuple[LCTTSourceVisibleRow, ...], policy: LCTTDirectMappingPolicy
) -> dict[str, tuple[LCTTSourceVisibleRow, float]]:
    selected: dict[str, tuple[LCTTSourceVisibleRow, float]] = {}
    used_rows: set[str] = set()
    for rule in policy.composite_rules:
        ranked = sorted(
            (
                ratio(retrieval_key(row.visible_label), rule.visible_label_anchor) / 100,
                -row.order,
                row,
            )
            for row in rows
        )
        best_score, _negative_order, best_row = ranked[-1]
        runner_up = ranked[-2][0]
        if (
            best_score < rule.minimum_anchor_similarity
            or best_score - runner_up < policy.minimum_composite_anchor_runner_up_margin
            or best_row.row_id in used_rows
        ):
            raise LCTTItemMappingError(f"LCTT composite row {rule.key} is unresolved")
        used_rows.add(best_row.row_id)
        selected[rule.key] = (best_row, best_score)
    return selected


def reconcile_lctt_direct_items(
    logical_rows: Sequence[object],
    *,
    schema: Sequence[SchemaItem],
    policy: LCTTDirectMappingPolicy,
    report_scope: str,
    cash_flow_method: CashFlowMethod | str,
    source_reader_id: str = "ppocrv6-word-box",
) -> LCTTItemMappingResult:
    """Expose all 107 schema outcomes while withholding automatic selections."""

    method = CashFlowMethod(str(cash_flow_method))
    if method is not CashFlowMethod.DIRECT:
        raise LCTTItemMappingError("LCTT direct reconciliation requires visible DIRECT method")
    scope = str(report_scope).upper()
    if scope not in {"CONSOLIDATED", "SEPARATE"}:
        raise LCTTItemMappingError("LCTT report scope must be visibly resolved")
    rows = adapt_lctt_logical_rows(logical_rows, source_reader_id=source_reader_id)
    projection = build_lctt_direct_schema_projection(schema)
    all_lctt = tuple(
        sorted(
            (item for item in schema if item.statement_type == "LCTT"),
            key=lambda item: item.display_order,
        )
    )
    if len(all_lctt) != LCTT_SCHEMA_ITEM_COUNT:
        raise LCTTItemMappingError("LCTT schema denominator must be exactly 107")
    direct_by_id = projection.by_id()
    if any(
        report_norm_id not in direct_by_id for report_norm_id in policy.not_observed_report_norm_ids
    ):
        raise LCTTItemMappingError("LCTT not-observed policy references a non-direct item")
    composite_by_id: dict[int, LCTTCompositeRule] = {}
    for rule in policy.composite_rules:
        for report_norm_id in rule.candidate_report_norm_ids:
            if report_norm_id not in direct_by_id:
                raise LCTTItemMappingError("LCTT composite policy references a non-direct item")
            composite_by_id[report_norm_id] = rule
    composites = _identify_composites(rows, policy)
    composite_row_ids = {row.row_id for row, _score in composites.values()}
    excluded_direct_ids = {
        *policy.not_observed_report_norm_ids,
        *composite_by_id,
    }
    candidate_nodes = tuple(
        node for node in projection.nodes if node.report_norm_id not in excluded_direct_ids
    )
    candidate_rows = tuple(row for row in rows if row.row_id not in composite_row_ids)
    if len(candidate_nodes) != 41 or len(candidate_rows) != 41:
        raise LCTTItemMappingError("LCTT monotone candidate denominator does not reconcile to 41")

    candidate_by_schema: dict[int, tuple[LCTTSourceVisibleRow, float]] = {}
    candidate_by_row: dict[str, tuple[int, float]] = {}
    for row, node in zip(candidate_rows, candidate_nodes, strict=True):
        similarity = _label_similarity(row.visible_label, node)
        if similarity < policy.minimum_monotone_candidate_label_score:
            raise LCTTItemMappingError(
                f"LCTT monotone candidate {row.row_id}->{node.report_norm_id} is unsupported"
            )
        candidate_by_schema[node.report_norm_id] = (row, similarity)
        candidate_by_row[row.row_id] = (node.report_norm_id, similarity)

    composite_source: dict[str, tuple[LCTTCompositeRule, float]] = {}
    for rule in policy.composite_rules:
        row, similarity = composites[rule.key]
        composite_source[row.row_id] = (rule, similarity)
    schema_dispositions = []
    for item in all_lctt:
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
        elif item.schema_id in composite_by_id:
            status = LCTTSchemaStatus.AMBIGUOUS_MAPPING
            rule = composite_by_id[item.schema_id]
            source_row, similarity = composites[rule.key]
            candidate_rows_for_item = (source_row.row_id,)
            reason = (
                f"visible composite row {rule.key} spans multiple ReportNormIds; "
                "single-ID selection is withheld"
            )
        else:
            status = LCTTSchemaStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            source_row, similarity = candidate_by_schema[item.schema_id]
            candidate_rows_for_item = (source_row.row_id,)
            reason = (
                "one-to-one monotone DIRECT-branch candidate supported by visible label/order; "
                "only one semantic stream is available"
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
                reason=reason,
            )
        )
    source_dispositions = []
    for row in rows:
        if row.row_id in composite_source:
            rule, similarity = composite_source[row.row_id]
            status = LCTTSourceRowStatus.SOURCE_ONLY_PDF_ROW
            candidate_ids = rule.candidate_report_norm_ids
            reason = (
                f"visible composite row {rule.key} is retained source-only pending cell-level "
                "accounting/schema resolution"
            )
        else:
            report_norm_id, similarity = candidate_by_row[row.row_id]
            status = LCTTSourceRowStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC
            candidate_ids = (report_norm_id,)
            reason = (
                "one-to-one monotone candidate only; no second independent semantic label stream"
            )
        source_dispositions.append(
            LCTTSourceDisposition(
                row_id=row.row_id,
                order=row.order,
                page_tag=row.page_tag,
                visible_label=row.visible_label,
                status=status.value,
                candidate_report_norm_ids=candidate_ids,
                label_similarity=round(similarity, 6),
                reason=reason,
            )
        )
    result = LCTTItemMappingResult(
        statement_type="LCTT",
        report_scope=scope,
        cash_flow_method=method.value,
        status="CANDIDATE_RECONCILIATION",
        automatic_selection_allowed=False,
        independent_semantic_stream_count=policy.currently_available_independent_semantic_streams,
        minimum_independent_semantic_streams=policy.minimum_independent_semantic_streams,
        schema_item_count=LCTT_SCHEMA_ITEM_COUNT,
        schema_status_reconciled_count=LCTT_SCHEMA_ITEM_COUNT,
        mapped_schema_count=0,
        candidate_linked_schema_count=41,
        ambiguous_schema_count=5,
        not_observed_schema_count=4,
        not_applicable_schema_count=57,
        fully_verified_schema_count=0,
        source_row_count=len(rows),
        candidate_linked_source_row_count=41,
        source_only_row_count=2,
        schema_dispositions=tuple(schema_dispositions),
        source_dispositions=tuple(source_dispositions),
        schema_projection_sha256=projection.projection_sha256,
        policy_sha256=policy.policy_sha256,
        source_label_sha256=_source_label_digest(rows),
        mapping_inputs=_MAPPING_INPUTS,
        reason=(
            "all schema/source statuses reconcile, but one PP-OCR label stream cannot authorize "
            "automatic ReportNormId selection"
        ),
    )
    return validate_lctt_item_mapping_result(result)


def validate_lctt_item_mapping_result(result: LCTTItemMappingResult) -> LCTTItemMappingResult:
    """Validate denominators, candidate cross-links, and fail-closed selection state."""

    if (
        result.statement_type != "LCTT"
        or result.status != "CANDIDATE_RECONCILIATION"
        or result.automatic_selection_allowed
        or result.independent_semantic_stream_count >= result.minimum_independent_semantic_streams
        or result.schema_item_count != LCTT_SCHEMA_ITEM_COUNT
        or result.schema_status_reconciled_count != LCTT_SCHEMA_ITEM_COUNT
        or result.mapped_schema_count != 0
        or result.fully_verified_schema_count != 0
        or result.source_row_count != LCTT_VISIBLE_SOURCE_ROW_COUNT
        or result.mapping_inputs != _MAPPING_INPUTS
        or _SHA256.fullmatch(result.schema_projection_sha256) is None
        or _SHA256.fullmatch(result.policy_sha256) is None
        or _SHA256.fullmatch(result.source_label_sha256) is None
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
        LCTTSchemaStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value: (
            result.candidate_linked_schema_count
        ),
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
        sum(
            item.status == LCTTSourceRowStatus.CANDIDATE_MAPPING_NOT_AUTOMATIC.value
            for item in source
        )
        != result.candidate_linked_source_row_count
        or sum(item.status == LCTTSourceRowStatus.SOURCE_ONLY_PDF_ROW.value for item in source)
        != result.source_only_row_count
        or result.candidate_linked_source_row_count + result.source_only_row_count
        != LCTT_VISIBLE_SOURCE_ROW_COUNT
    ):
        raise LCTTItemMappingError("LCTT source reconciliation counts drifted")
    source_by_id = {item.row_id: item for item in source}
    schema_by_id = {item.report_norm_id: item for item in schema}
    for item in schema:
        if any(row_id not in source_by_id for row_id in item.candidate_source_row_ids):
            raise LCTTItemMappingError("LCTT schema candidate references an unknown source row")
        for row_id in item.candidate_source_row_ids:
            if item.report_norm_id not in source_by_id[row_id].candidate_report_norm_ids:
                raise LCTTItemMappingError(
                    "LCTT schema/source candidate cross-link is inconsistent"
                )
    for item in source:
        if any(
            report_norm_id not in schema_by_id for report_norm_id in item.candidate_report_norm_ids
        ):
            raise LCTTItemMappingError("LCTT source candidate references an unknown schema item")
    return result


__all__ = [
    "LCTTCompositeRule",
    "LCTTDirectMappingPolicy",
    "LCTTItemMappingError",
    "LCTTItemMappingResult",
    "LCTTSchemaDisposition",
    "LCTTSchemaStatus",
    "LCTTSourceDisposition",
    "LCTTSourceRowStatus",
    "LCTTSourceVisibleRow",
    "LCTT_DIRECT_SCHEMA_ITEM_COUNT",
    "LCTT_INDIRECT_SCHEMA_ITEM_COUNT",
    "LCTT_POLICY_RELATIVE_PATH",
    "LCTT_SCHEMA_ITEM_COUNT",
    "LCTT_TRAILING_AGGREGATE_IDS",
    "LCTT_VISIBLE_SOURCE_ROW_COUNT",
    "adapt_lctt_logical_rows",
    "build_lctt_direct_schema_projection",
    "load_lctt_direct_mapping_policy",
    "reconcile_lctt_direct_items",
    "validate_lctt_item_mapping_result",
]
