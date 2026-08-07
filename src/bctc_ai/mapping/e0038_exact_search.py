from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any

import yaml

from bctc_ai.mapping.ordered_subgraph_v2 import (
    IntervalDiagnostic,
    OrderedSubgraphV2Policy,
    OrderedSubgraphV2Result,
    SchemaProjectionNodeV2,
    SchemaProjectionV2,
    SourceStructureRowV2,
    _anchor_prepass,
    _ordered_projection_nodes,
    _partition_intervals,
    _validated_rows,
    align_ordered_subgraph_v2,
    load_ordered_subgraph_v2_policy_bytes,
)

E0037_REFERENCE_BEAM_WIDTH = 64
E0037_MAX_MONOTONE_SIGNATURE_BOUND = 5005
E0038_EXACT_SEARCH_HARD_CAP = 8192
E0038_MAX_INTERVAL_COUNT = 65
E0038_MAX_SOURCE_ROW_COUNT = 64
E0038_MAX_SCHEMA_NODE_COUNT = 77
E0038_MAX_ROW_ID_LENGTH = 128
E0038_MAX_DP_CELL_BUDGET = 16384
E0038_MAX_READER_COUNT_PER_ROW = 16
E0038_MAX_READER_ID_LENGTH = 128
E0038_MAX_LABEL_LENGTH = 4096
E0038_MAX_TOTAL_SIGNATURE_WORK = 150000
E0038_MAX_STRUCTURAL_ALIASES_PER_NODE = 32
E0038_MAX_CHILDREN_PER_NODE = 77
E0038_MAX_SECTION_PATH_DEPTH = 16
E0038_MAX_SCOPES_PER_NODE = 8

_MAPPING_PROXY_TYPE = type(MappingProxyType({}))


class E0038ExactSearchError(ValueError):
    """Raised when E-0038 receives malformed or policy-incompatible evidence."""


class E0038ExactSearchStatus(StrEnum):
    EXACT_SEARCH_COMPLETE = "EXACT_SEARCH_COMPLETE"
    ABSTAINED_E0037_BOUND_EXCEEDED = "ABSTAINED_E0037_BOUND_EXCEEDED"
    ABSTAINED_HARD_CAP_EXCEEDED = "ABSTAINED_HARD_CAP_EXCEEDED"
    ABSTAINED_TOTAL_WORK_CAP_EXCEEDED = "ABSTAINED_TOTAL_WORK_CAP_EXCEEDED"
    ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT = "ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT"
    ABSTAINED_NONZERO_PRUNING = "ABSTAINED_NONZERO_PRUNING"


@dataclass(frozen=True)
class E0038IntervalSignatureBound:
    interval_index: int
    previous_anchor_row_id: str | None
    previous_anchor_report_norm_id: int | None
    next_anchor_row_id: str | None
    next_anchor_report_norm_id: int | None
    row_count: int
    schema_node_count: int
    monotone_signature_bound: int
    cell_signature_sum_bound: int
    worst_case_search_multiplier: int
    total_signature_work_bound: int
    row_ids: tuple[str, ...]
    report_norm_ids: tuple[int, ...]


@dataclass(frozen=True)
class E0038ExactSearchPlan:
    status: E0038ExactSearchStatus | None
    reason: str
    interval_bounds: tuple[E0038IntervalSignatureBound, ...]
    maximum_monotone_signature_bound: int
    total_dp_cells: int = 0
    total_cell_signature_sum_bound: int = 0
    total_signature_work_bound: int = 0
    e0037_bound_limit: int = E0037_MAX_MONOTONE_SIGNATURE_BOUND
    hard_cap: int = E0038_EXACT_SEARCH_HARD_CAP
    total_signature_work_cap: int = E0038_MAX_TOTAL_SIGNATURE_WORK

    @property
    def eligible(self) -> bool:
        return self.status is None


@dataclass(frozen=True)
class E0038ExactSearchOutcome:
    status: E0038ExactSearchStatus
    reason: str
    plan: E0038ExactSearchPlan
    align_invocation_count: int
    main_search_pruned_states: int
    counterfactual_search_pruned_states: int
    result: OrderedSubgraphV2Result | None


def _validated_policy_payload(policy: OrderedSubgraphV2Policy) -> dict[str, Any]:
    if type(policy) is not OrderedSubgraphV2Policy or type(policy.source_bytes) is not bytes:
        raise E0038ExactSearchError("mapping policy object/bytes have invalid runtime types")
    if (
        type(policy.version) is not int
        or type(policy.mode) is not str
        or type(policy.calibration_status) is not str
        or type(policy.ordering_authority) is not str
        or type(policy.minimum_anchor_stream_score) is not float
        or type(policy.minimum_anchor_stream_margin) is not float
        or type(policy.minimum_anchor_streams) is not int
        or type(policy.minimum_strong_label_score) is not float
        or type(policy.minimum_parent_relaxed_label_score) is not float
        or type(policy.parent_relaxed_relation_type) is not str
        or type(policy.minimum_interval_margin) is not float
        or type(policy.beam_width) is not int
        or type(policy.returned_path_limit) is not int
        or type(policy.parent_corroboration_gain) is not float
        or type(policy.trailing_aggregate_ids) is not tuple
        or any(type(item) is not int for item in policy.trailing_aggregate_ids)
        or type(policy.policy_sha256) is not str
    ):
        raise E0038ExactSearchError("mapping policy contains non-canonical runtime fields")
    if hashlib.sha256(policy.source_bytes).hexdigest() != policy.policy_sha256:
        raise E0038ExactSearchError("mapping policy byte/hash identity drifted")
    canonical = load_ordered_subgraph_v2_policy_bytes(
        policy.source_bytes,
        source_path=policy.source_path,
    )
    if canonical != policy:
        raise E0038ExactSearchError("mapping policy object differs from its immutable bytes")
    payload = yaml.safe_load(policy.source_bytes.decode("utf-8"))
    if not isinstance(payload, dict):
        raise E0038ExactSearchError("mapping policy payload is not an object")
    return payload


def validate_e0038_policy_parity(
    e0037_policy: OrderedSubgraphV2Policy,
    exact_policy: OrderedSubgraphV2Policy,
) -> None:
    """Require byte-semantic parity with E-0037 except for the exact-search beam."""

    e0037_payload = deepcopy(_validated_policy_payload(e0037_policy))
    exact_payload = deepcopy(_validated_policy_payload(exact_policy))
    if e0037_policy.beam_width != E0037_REFERENCE_BEAM_WIDTH:
        raise E0038ExactSearchError("E-0037 reference policy does not retain its sealed beam width")
    if exact_policy.beam_width != E0038_EXACT_SEARCH_HARD_CAP:
        raise E0038ExactSearchError("E-0038 exact policy must use the hard-cap beam width")

    for label, payload, expected_beam in (
        ("E-0037", e0037_payload, E0037_REFERENCE_BEAM_WIDTH),
        ("E-0038", exact_payload, E0038_EXACT_SEARCH_HARD_CAP),
    ):
        search = payload.get("search")
        if not isinstance(search, dict):
            raise E0038ExactSearchError(f"{label} policy search block is invalid")
        if search.get("beam_width_per_dp_cell") != expected_beam:
            raise E0038ExactSearchError(f"{label} policy beam bytes/object disagree")
        del search["beam_width_per_dp_cell"]

    if e0037_payload != exact_payload:
        raise E0038ExactSearchError(
            "E-0038 policy changes mapping semantics beyond beam_width_per_dp_cell"
        )


def _validated_row_ids(value: object, *, interval_index: int) -> tuple[str, ...]:
    if type(value) not in (list, tuple):
        raise E0038ExactSearchError(f"sealed interval {interval_index} row_ids are not a sequence")
    if len(value) > E0038_MAX_SOURCE_ROW_COUNT:
        raise E0038ExactSearchError(
            f"sealed interval {interval_index} exceeds the source-row budget"
        )
    result = tuple(value)
    if any(
        not isinstance(item, str) or not item or len(item) > E0038_MAX_ROW_ID_LENGTH
        for item in result
    ):
        raise E0038ExactSearchError(f"sealed interval {interval_index} has an invalid row_id")
    if len(result) != len(set(result)):
        raise E0038ExactSearchError(f"sealed interval {interval_index} repeats a row_id")
    return result


def _validated_report_norm_ids(value: object, *, interval_index: int) -> tuple[int, ...]:
    if type(value) not in (list, tuple):
        raise E0038ExactSearchError(
            f"sealed interval {interval_index} report_norm_ids are not a sequence"
        )
    if len(value) > E0038_MAX_SCHEMA_NODE_COUNT:
        raise E0038ExactSearchError(
            f"sealed interval {interval_index} exceeds the schema-node budget"
        )
    result = tuple(value)
    if any(type(item) is not int or item <= 0 or item > 2**31 - 1 for item in result):
        raise E0038ExactSearchError(f"sealed interval {interval_index} has an invalid ReportNormId")
    if len(result) != len(set(result)):
        raise E0038ExactSearchError(f"sealed interval {interval_index} repeats a ReportNormId")
    return result


def _validated_anchor_identity(
    diagnostic: Mapping[str, object],
    *,
    prefix: str,
    interval_index: int,
) -> tuple[str | None, int | None]:
    row_id = diagnostic.get(f"{prefix}_anchor_row_id")
    report_norm_id = diagnostic.get(f"{prefix}_anchor_report_norm_id")
    if row_id is None and report_norm_id is None:
        return None, None
    if (
        not isinstance(row_id, str)
        or not row_id
        or len(row_id) > E0038_MAX_ROW_ID_LENGTH
        or type(report_norm_id) is not int
        or report_norm_id <= 0
        or report_norm_id > 2**31 - 1
    ):
        raise E0038ExactSearchError(
            f"sealed interval {interval_index} has an invalid {prefix} anchor identity"
        )
    return row_id, report_norm_id


def _bounded_combination(total: int, choose: int, *, maximum: int) -> int:
    """Return ``C(total, choose)`` or ``maximum + 1`` without a large integer."""

    choose = min(choose, total - choose)
    result = 1
    for step in range(1, choose + 1):
        result = result * (total - choose + step) // step
        if result > maximum:
            return maximum + 1
    return result


def _bounded_monotone_signature_count(row_count: int, schema_node_count: int) -> int:
    """Return C(m+n,m), saturating before a hostile big integer is created."""

    return _bounded_combination(
        row_count + schema_node_count,
        row_count,
        maximum=E0038_EXACT_SEARCH_HARD_CAP,
    )


def _bounded_cell_signature_sum(row_count: int, schema_node_count: int) -> int:
    """Bound signatures retained across every DP cell: C(m+n+2,m+1)-1."""

    combination = _bounded_combination(
        row_count + schema_node_count + 2,
        row_count + 1,
        maximum=E0038_MAX_TOTAL_SIGNATURE_WORK + 1,
    )
    return min(combination - 1, E0038_MAX_TOTAL_SIGNATURE_WORK + 1)


def _bounded_product(left: int, right: int, *, maximum: int) -> int:
    if left > maximum // right:
        return maximum + 1
    return left * right


def _bounded_sum(values: Sequence[int], *, maximum: int) -> int:
    result = 0
    for value in values:
        if value > maximum - result:
            return maximum + 1
        result += value
    return result


def _boundary_pair(
    interval: E0038IntervalSignatureBound,
    *,
    side: str,
) -> tuple[str | None, int | None]:
    if side == "previous":
        return interval.previous_anchor_row_id, interval.previous_anchor_report_norm_id
    return interval.next_anchor_row_id, interval.next_anchor_report_norm_id


def _partition_chain_error(
    bounds: Sequence[E0038IntervalSignatureBound],
) -> str | None:
    null_boundary = (None, None)
    if _boundary_pair(bounds[0], side="previous") != null_boundary:
        return "first sealed interval has a non-null previous anchor"
    if _boundary_pair(bounds[-1], side="next") != null_boundary:
        return "last sealed interval has a non-null next anchor"

    interior_rows = {row_id for interval in bounds for row_id in interval.row_ids}
    interior_nodes = {
        report_norm_id for interval in bounds for report_norm_id in interval.report_norm_ids
    }
    anchor_rows: set[str] = set()
    anchor_nodes: set[int] = set()
    for left, right in zip(bounds, bounds[1:], strict=False):
        left_next = _boundary_pair(left, side="next")
        right_previous = _boundary_pair(right, side="previous")
        if left_next == null_boundary or right_previous == null_boundary:
            return "adjacent sealed intervals have a null internal anchor boundary"
        if left_next != right_previous:
            return "adjacent sealed interval anchor boundaries do not match"
        anchor_row_id, anchor_report_norm_id = left_next
        if anchor_row_id in interior_rows or anchor_report_norm_id in interior_nodes:
            return "sealed anchor identity is also present in an interval interior"
        if anchor_row_id in anchor_rows or anchor_report_norm_id in anchor_nodes:
            return "sealed interval chain repeats an anchor identity"
        anchor_rows.add(anchor_row_id)
        anchor_nodes.add(anchor_report_norm_id)
    return None


def _interleaved_partition_ids(
    bounds: Sequence[E0038IntervalSignatureBound],
) -> tuple[tuple[str, ...], tuple[int, ...]]:
    row_ids: list[str] = []
    report_norm_ids: list[int] = []
    for interval in bounds:
        row_ids.extend(interval.row_ids)
        report_norm_ids.extend(interval.report_norm_ids)
        if interval.next_anchor_row_id is not None:
            if interval.next_anchor_report_norm_id is None:
                raise E0038ExactSearchError("sealed interval has a partial next anchor identity")
            row_ids.append(interval.next_anchor_row_id)
            report_norm_ids.append(interval.next_anchor_report_norm_id)
    return tuple(row_ids), tuple(report_norm_ids)


def plan_e0038_exact_search(
    sealed_interval_diagnostics: Sequence[Mapping[str, object]],
) -> E0038ExactSearchPlan:
    """Bound every sealed interval before permitting the exact-policy invocation.

    A monotone row/node path signature is a non-crossing partial matching. For
    ``m`` rows and ``n`` schema nodes, the number of possible signatures is at
    most ``sum(comb(m, k) * comb(n, k)) == comb(m + n, m)``. The bound is
    deliberately independent of labels, scores, or mapping outcomes.
    """

    if type(sealed_interval_diagnostics) not in (list, tuple):
        raise E0038ExactSearchError("sealed interval diagnostics must be a concrete sequence")
    if not sealed_interval_diagnostics:
        raise E0038ExactSearchError("sealed interval diagnostics are empty")
    if len(sealed_interval_diagnostics) > E0038_MAX_INTERVAL_COUNT:
        raise E0038ExactSearchError("sealed interval diagnostics exceed the interval budget")

    bounds: list[E0038IntervalSignatureBound] = []
    seen_rows: set[str] = set()
    seen_nodes: set[int] = set()
    for expected_index, diagnostic in enumerate(sealed_interval_diagnostics):
        if type(diagnostic) is not dict:
            raise E0038ExactSearchError(
                f"sealed interval diagnostic {expected_index} is not an object"
            )
        interval_index = diagnostic.get("interval_index")
        if (
            isinstance(interval_index, bool)
            or not isinstance(interval_index, int)
            or interval_index != expected_index
        ):
            raise E0038ExactSearchError(
                "sealed interval indices must be unique, contiguous, and ordered from zero"
            )
        row_ids = _validated_row_ids(
            diagnostic.get("row_ids"),
            interval_index=interval_index,
        )
        report_norm_ids = _validated_report_norm_ids(
            diagnostic.get("report_norm_ids"),
            interval_index=interval_index,
        )
        previous_anchor_row_id, previous_anchor_report_norm_id = _validated_anchor_identity(
            diagnostic,
            prefix="previous",
            interval_index=interval_index,
        )
        next_anchor_row_id, next_anchor_report_norm_id = _validated_anchor_identity(
            diagnostic,
            prefix="next",
            interval_index=interval_index,
        )
        duplicate_rows = seen_rows.intersection(row_ids)
        duplicate_nodes = seen_nodes.intersection(report_norm_ids)
        if duplicate_rows:
            raise E0038ExactSearchError(
                f"sealed intervals repeat source rows: {sorted(duplicate_rows)}"
            )
        if duplicate_nodes:
            raise E0038ExactSearchError(
                f"sealed intervals repeat schema nodes: {sorted(duplicate_nodes)}"
            )
        seen_rows.update(row_ids)
        seen_nodes.update(report_norm_ids)
        row_count = len(row_ids)
        schema_node_count = len(report_norm_ids)
        cell_signature_sum = _bounded_cell_signature_sum(row_count, schema_node_count)
        search_multiplier = 1 + min(row_count, schema_node_count)
        signature_work = _bounded_product(
            cell_signature_sum,
            search_multiplier,
            maximum=E0038_MAX_TOTAL_SIGNATURE_WORK,
        )
        bounds.append(
            E0038IntervalSignatureBound(
                interval_index=interval_index,
                previous_anchor_row_id=previous_anchor_row_id,
                previous_anchor_report_norm_id=previous_anchor_report_norm_id,
                next_anchor_row_id=next_anchor_row_id,
                next_anchor_report_norm_id=next_anchor_report_norm_id,
                row_count=row_count,
                schema_node_count=schema_node_count,
                monotone_signature_bound=_bounded_monotone_signature_count(
                    row_count,
                    schema_node_count,
                ),
                cell_signature_sum_bound=cell_signature_sum,
                worst_case_search_multiplier=search_multiplier,
                total_signature_work_bound=signature_work,
                row_ids=row_ids,
                report_norm_ids=report_norm_ids,
            )
        )

    frozen_bounds = tuple(bounds)
    chain_error = _partition_chain_error(frozen_bounds)
    interleaved_rows, interleaved_nodes = _interleaved_partition_ids(frozen_bounds)
    if len(interleaved_rows) != len(set(interleaved_rows)):
        chain_error = chain_error or "sealed interval chain repeats an ordered source row"
    if len(interleaved_nodes) != len(set(interleaved_nodes)):
        chain_error = chain_error or "sealed interval chain repeats an ordered schema node"
    if len(interleaved_rows) > E0038_MAX_SOURCE_ROW_COUNT:
        raise E0038ExactSearchError("sealed intervals exceed the total source-row budget")
    if len(interleaved_nodes) > E0038_MAX_SCHEMA_NODE_COUNT:
        raise E0038ExactSearchError("sealed intervals exceed the total schema-node budget")
    dp_cells = sum((item.row_count + 1) * (item.schema_node_count + 1) for item in bounds)
    if dp_cells > E0038_MAX_DP_CELL_BUDGET:
        raise E0038ExactSearchError("sealed intervals exceed the DP-cell work budget")

    maximum = max(item.monotone_signature_bound for item in frozen_bounds)
    total_cell_signatures = _bounded_sum(
        [item.cell_signature_sum_bound for item in frozen_bounds],
        maximum=E0038_MAX_TOTAL_SIGNATURE_WORK,
    )
    total_signature_work = _bounded_sum(
        [item.total_signature_work_bound for item in frozen_bounds],
        maximum=E0038_MAX_TOTAL_SIGNATURE_WORK,
    )
    common_plan_fields = {
        "interval_bounds": frozen_bounds,
        "maximum_monotone_signature_bound": maximum,
        "total_dp_cells": dp_cells,
        "total_cell_signature_sum_bound": total_cell_signatures,
        "total_signature_work_bound": total_signature_work,
    }
    if chain_error is not None:
        return E0038ExactSearchPlan(
            status=E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT,
            reason=f"{chain_error}; aligner was not invoked",
            **common_plan_fields,
        )
    if maximum > E0038_EXACT_SEARCH_HARD_CAP:
        return E0038ExactSearchPlan(
            status=E0038ExactSearchStatus.ABSTAINED_HARD_CAP_EXCEEDED,
            reason=(
                f"sealed interval signature bound {maximum} exceeds hard cap "
                f"{E0038_EXACT_SEARCH_HARD_CAP}; aligner was not invoked"
            ),
            **common_plan_fields,
        )
    if maximum > E0037_MAX_MONOTONE_SIGNATURE_BOUND:
        return E0038ExactSearchPlan(
            status=E0038ExactSearchStatus.ABSTAINED_E0037_BOUND_EXCEEDED,
            reason=(
                f"sealed interval signature bound {maximum} exceeds the E-0037 audited "
                f"maximum {E0037_MAX_MONOTONE_SIGNATURE_BOUND}; aligner was not invoked"
            ),
            **common_plan_fields,
        )
    if total_signature_work > E0038_MAX_TOTAL_SIGNATURE_WORK:
        return E0038ExactSearchPlan(
            status=E0038ExactSearchStatus.ABSTAINED_TOTAL_WORK_CAP_EXCEEDED,
            reason=(
                f"worst-case exact-search signature work exceeds cap "
                f"{E0038_MAX_TOTAL_SIGNATURE_WORK}; aligner was not invoked"
            ),
            **common_plan_fields,
        )
    return E0038ExactSearchPlan(
        status=None,
        reason=(
            f"all sealed interval signature bounds are at most {maximum}, within the "
            f"E-0037 limit {E0037_MAX_MONOTONE_SIGNATURE_BOUND} and hard cap "
            f"{E0038_EXACT_SEARCH_HARD_CAP}; worst-case signature work is "
            f"{total_signature_work} within cap {E0038_MAX_TOTAL_SIGNATURE_WORK}"
        ),
        **common_plan_fields,
    )


def _interval_identity(interval: IntervalDiagnostic) -> tuple[object, ...]:
    return (
        interval.interval_index,
        interval.previous_anchor_row_id,
        interval.previous_anchor_report_norm_id,
        interval.next_anchor_row_id,
        interval.next_anchor_report_norm_id,
        tuple(interval.row_ids),
        tuple(interval.report_norm_ids),
    )


def _bound_identity(interval: E0038IntervalSignatureBound) -> tuple[object, ...]:
    return (
        interval.interval_index,
        interval.previous_anchor_row_id,
        interval.previous_anchor_report_norm_id,
        interval.next_anchor_row_id,
        interval.next_anchor_report_norm_id,
        interval.row_ids,
        interval.report_norm_ids,
    )


def _freeze_rows(rows: Sequence[SourceStructureRowV2]) -> tuple[SourceStructureRowV2, ...]:
    if type(rows) not in (list, tuple):
        raise E0038ExactSearchError("source rows must be a concrete sequence")
    if len(rows) > E0038_MAX_SOURCE_ROW_COUNT:
        raise E0038ExactSearchError("source rows exceed the E-0038 budget")
    frozen: list[SourceStructureRowV2] = []
    for row in rows:
        if type(row) is not SourceStructureRowV2:
            raise E0038ExactSearchError("source rows contain a foreign object")
        if (
            not isinstance(row.row_id, str)
            or not row.row_id
            or len(row.row_id) > E0038_MAX_ROW_ID_LENGTH
            or type(row.order) is not int
            or row.order < 0
        ):
            raise E0038ExactSearchError("source rows contain an invalid identity or order")
        if row.parent_row_id is not None and (
            not isinstance(row.parent_row_id, str)
            or not row.parent_row_id
            or len(row.parent_row_id) > E0038_MAX_ROW_ID_LENGTH
        ):
            raise E0038ExactSearchError(f"row {row.row_id} has an invalid parent identity")
        if type(row.labels_by_reader) not in (dict, _MAPPING_PROXY_TYPE):
            raise E0038ExactSearchError(f"row {row.row_id} labels are not a concrete mapping")
        if len(row.labels_by_reader) > E0038_MAX_READER_COUNT_PER_ROW:
            raise E0038ExactSearchError(f"row {row.row_id} exceeds the reader-label budget")
        labels = tuple(row.labels_by_reader.items())
        if len(labels) != len({key for key, _value in labels}):
            raise E0038ExactSearchError(f"row {row.row_id} repeats a reader label")
        if any(
            type(key) is not str
            or not key
            or len(key) > E0038_MAX_READER_ID_LENGTH
            or type(value) is not str
            or len(value) > E0038_MAX_LABEL_LENGTH
            for key, value in labels
        ):
            raise E0038ExactSearchError(f"row {row.row_id} has an invalid reader label")
        if (
            type(row.row_role) is not str
            or len(row.row_role) > 64
            or type(row.relation_type) is not str
            or len(row.relation_type) > 64
            or type(row.report_scope) is not str
            or len(row.report_scope) > 64
            or type(row.target_template_in_scope) is not bool
        ):
            raise E0038ExactSearchError(f"row {row.row_id} has invalid structural fields")
        frozen.append(
            SourceStructureRowV2(
                row_id=row.row_id,
                order=row.order,
                labels_by_reader=MappingProxyType(dict(sorted(labels))),
                row_role=row.row_role,
                parent_row_id=row.parent_row_id,
                relation_type=row.relation_type,
                report_scope=row.report_scope,
                target_template_in_scope=row.target_template_in_scope,
            )
        )
    return tuple(frozen)


def _source_rows_digest(rows: Sequence[SourceStructureRowV2]) -> str:
    payload = [
        {
            "labels_by_reader": sorted(row.labels_by_reader.items()),
            "order": row.order,
            "parent_row_id": row.parent_row_id,
            "relation_type": row.relation_type,
            "report_scope": row.report_scope,
            "row_id": row.row_id,
            "row_role": row.row_role,
            "target_template_in_scope": row.target_template_in_scope,
        }
        for row in rows
    ]
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _freeze_projection(projection: SchemaProjectionV2) -> SchemaProjectionV2:
    if type(projection) is not SchemaProjectionV2 or type(projection.nodes) not in (list, tuple):
        raise E0038ExactSearchError("schema projection has invalid runtime types")
    if len(projection.nodes) > E0038_MAX_SCHEMA_NODE_COUNT:
        raise E0038ExactSearchError("schema projection exceeds the E-0038 schema budget")
    for node in projection.nodes:
        if type(node) is not SchemaProjectionNodeV2:
            raise E0038ExactSearchError("schema projection contains a foreign node")
        sequences = (
            node.structural_aliases,
            node.child_report_norm_ids,
            node.section_path,
            node.scopes,
        )
        if any(type(value) not in (list, tuple) for value in sequences):
            raise E0038ExactSearchError("schema projection contains a non-concrete sequence")
        if (
            len(node.structural_aliases) > E0038_MAX_STRUCTURAL_ALIASES_PER_NODE
            or len(node.child_report_norm_ids) > E0038_MAX_CHILDREN_PER_NODE
            or len(node.section_path) > E0038_MAX_SECTION_PATH_DEPTH
            or len(node.scopes) > E0038_MAX_SCOPES_PER_NODE
        ):
            raise E0038ExactSearchError("schema projection exceeds a nested sequence budget")
    nodes = _ordered_projection_nodes(projection)
    frozen_nodes = tuple(
        SchemaProjectionNodeV2(
            report_norm_id=node.report_norm_id,
            canonical_name=node.canonical_name,
            structural_aliases=tuple(node.structural_aliases),
            statement_type=node.statement_type,
            display_order=node.display_order,
            parent_report_norm_id=node.parent_report_norm_id,
            child_report_norm_ids=tuple(node.child_report_norm_ids),
            hierarchy_level=node.hierarchy_level,
            section_path=tuple(node.section_path),
            scopes=tuple(node.scopes),
        )
        for node in nodes
    )
    frozen = SchemaProjectionV2(
        statement_type=projection.statement_type,
        nodes=frozen_nodes,
        projection_sha256=projection.projection_sha256,
        alias_authority=projection.alias_authority,
    )
    _ordered_projection_nodes(frozen)
    return frozen


def _plan_covers_ordered_universe(
    plan: E0038ExactSearchPlan,
    rows: Sequence[SourceStructureRowV2],
    projection: SchemaProjectionV2,
) -> bool:
    actual_rows, actual_nodes = _interleaved_partition_ids(plan.interval_bounds)
    expected_rows = tuple(row.row_id for row in _validated_rows(rows, projection))
    expected_nodes = tuple(node.report_norm_id for node in _ordered_projection_nodes(projection))
    return actual_rows == expected_rows and actual_nodes == expected_nodes


def _validate_projection_overlay(
    base_projection: SchemaProjectionV2,
    exact_projection: SchemaProjectionV2,
) -> None:
    if len(base_projection.nodes) > E0038_MAX_SCHEMA_NODE_COUNT:
        raise E0038ExactSearchError("base projection exceeds the E-0038 schema budget")
    if len(exact_projection.nodes) > E0038_MAX_SCHEMA_NODE_COUNT:
        raise E0038ExactSearchError("exact projection exceeds the E-0038 schema budget")
    base_nodes = _ordered_projection_nodes(base_projection)
    exact_nodes = _ordered_projection_nodes(exact_projection)
    if len(base_nodes) != len(exact_nodes):
        raise E0038ExactSearchError("exact projection changes the base node inventory")
    for base, exact in zip(base_nodes, exact_nodes, strict=True):
        if (
            base.report_norm_id != exact.report_norm_id
            or base.canonical_name != exact.canonical_name
            or base.statement_type != exact.statement_type
            or base.display_order != exact.display_order
            or base.parent_report_norm_id != exact.parent_report_norm_id
            or base.child_report_norm_ids != exact.child_report_norm_ids
            or base.hierarchy_level != exact.hierarchy_level
            or base.section_path != exact.section_path
            or base.scopes != exact.scopes
            or exact.structural_aliases[: len(base.structural_aliases)] != base.structural_aliases
        ):
            raise E0038ExactSearchError(
                "exact projection changes structure or non-additive base alias evidence"
            )


def _partition_diagnostics(
    rows: tuple[SourceStructureRowV2, ...],
    projection: SchemaProjectionV2,
    policy: OrderedSubgraphV2Policy,
) -> list[dict[str, object]]:
    ordered_rows = _validated_rows(rows, projection)
    nodes = _ordered_projection_nodes(projection)
    _diagnostics, anchors, _conflict, _reasons = _anchor_prepass(ordered_rows, nodes, policy)
    intervals = _partition_intervals(ordered_rows, nodes, anchors)
    return [
        {
            "interval_index": interval.index,
            "previous_anchor_row_id": (
                None if interval.previous_anchor is None else interval.previous_anchor.row_id
            ),
            "previous_anchor_report_norm_id": (
                None
                if interval.previous_anchor is None
                else interval.previous_anchor.report_norm_id
            ),
            "next_anchor_row_id": (
                None if interval.next_anchor is None else interval.next_anchor.row_id
            ),
            "next_anchor_report_norm_id": (
                None if interval.next_anchor is None else interval.next_anchor.report_norm_id
            ),
            "row_ids": [row.row_id for row in interval.rows],
            "report_norm_ids": [node.report_norm_id for node in interval.nodes],
        }
        for interval in intervals
    ]


def _valid_nonnegative_counter(value: object) -> bool:
    return type(value) is int and value >= 0


def run_e0038_exact_search(
    rows: Sequence[SourceStructureRowV2],
    projection: SchemaProjectionV2,
    *,
    base_projection: SchemaProjectionV2,
    sealed_interval_diagnostics: Sequence[Mapping[str, object]],
    e0037_policy: OrderedSubgraphV2Policy,
    exact_policy: OrderedSubgraphV2Policy,
) -> E0038ExactSearchOutcome:
    """Run immutable v2 only after bounds/parity pass, then reject any pruning."""

    validate_e0038_policy_parity(e0037_policy, exact_policy)
    sealed_plan = plan_e0038_exact_search(sealed_interval_diagnostics)
    if not sealed_plan.eligible:
        if sealed_plan.status is None:
            raise E0038ExactSearchError("ineligible exact-search plan has no abstention status")
        return E0038ExactSearchOutcome(
            status=sealed_plan.status,
            reason=sealed_plan.reason,
            plan=sealed_plan,
            align_invocation_count=0,
            main_search_pruned_states=0,
            counterfactual_search_pruned_states=0,
            result=None,
        )
    frozen_base_projection = _freeze_projection(base_projection)
    frozen_projection = _freeze_projection(projection)
    frozen_rows = _validated_rows(_freeze_rows(rows), frozen_base_projection)
    frozen_rows_sha256 = _source_rows_digest(frozen_rows)
    _validate_projection_overlay(frozen_base_projection, frozen_projection)
    sealed_identity = tuple(_bound_identity(item) for item in sealed_plan.interval_bounds)
    baseline_partition = plan_e0038_exact_search(
        _partition_diagnostics(frozen_rows, frozen_base_projection, e0037_policy)
    )
    baseline_identity = tuple(_bound_identity(item) for item in baseline_partition.interval_bounds)
    baseline_chain_valid = (
        sealed_plan.eligible
        and baseline_partition.eligible
        and _plan_covers_ordered_universe(
            sealed_plan,
            frozen_rows,
            frozen_base_projection,
        )
        and _plan_covers_ordered_universe(
            baseline_partition,
            frozen_rows,
            frozen_base_projection,
        )
    )
    if not baseline_chain_valid or baseline_identity != sealed_identity:
        return E0038ExactSearchOutcome(
            status=E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT,
            reason=(
                "frozen rows/base projection do not reproduce the full sealed E-0037 "
                "anchor and interval chain; exact aligner was not invoked"
            ),
            plan=sealed_plan,
            align_invocation_count=0,
            main_search_pruned_states=0,
            counterfactual_search_pruned_states=0,
            result=None,
        )

    plan = plan_e0038_exact_search(
        _partition_diagnostics(frozen_rows, frozen_projection, exact_policy)
    )
    if not plan.eligible:
        if plan.status is None:
            raise E0038ExactSearchError("ineligible exact-search plan has no abstention status")
        return E0038ExactSearchOutcome(
            status=plan.status,
            reason=plan.reason,
            plan=plan,
            align_invocation_count=0,
            main_search_pruned_states=0,
            counterfactual_search_pruned_states=0,
            result=None,
        )
    if not _plan_covers_ordered_universe(plan, frozen_rows, frozen_projection):
        return E0038ExactSearchOutcome(
            status=E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT,
            reason=(
                "exact alias partition does not interleave anchors and interiors over "
                "the complete frozen row/schema order; exact aligner was not invoked"
            ),
            plan=plan,
            align_invocation_count=0,
            main_search_pruned_states=0,
            counterfactual_search_pruned_states=0,
            result=None,
        )
    if plan.maximum_monotone_signature_bound > exact_policy.beam_width:
        raise E0038ExactSearchError(
            "eligible interval signature bound exceeds the exact policy beam"
        )

    result = align_ordered_subgraph_v2(frozen_rows, frozen_projection, policy=exact_policy)
    expected_intervals = tuple(_bound_identity(item) for item in plan.interval_bounds)
    actual_intervals = tuple(_interval_identity(item) for item in result.intervals)
    main_pruned = result.search.main_search_pruned_states
    counterfactual_pruned = result.search.counterfactual_search_pruned_states
    result_identity_valid = (
        result.policy_sha256 == exact_policy.policy_sha256
        and result.schema_projection_sha256 == frozen_projection.projection_sha256
        and result.schema_alias_authority == frozen_projection.alias_authority
        and result.search.algorithm == exact_policy.mode
        and result.search.beam_width_per_dp_cell == exact_policy.beam_width
        and result.search.intervals == len(result.intervals)
        and actual_intervals == expected_intervals
        and _source_rows_digest(frozen_rows) == frozen_rows_sha256
    )
    if not result_identity_valid:
        return E0038ExactSearchOutcome(
            status=E0038ExactSearchStatus.ABSTAINED_INTERVAL_DIAGNOSTIC_DRIFT,
            reason=(
                "exact-policy interval partition differs from sealed E-0037 diagnostics; "
                "mapping result was withheld"
            ),
            plan=plan,
            align_invocation_count=1,
            main_search_pruned_states=main_pruned,
            counterfactual_search_pruned_states=counterfactual_pruned,
            result=None,
        )

    interval_counters_valid = all(
        _valid_nonnegative_counter(item.main_search_pruned_states)
        and _valid_nonnegative_counter(item.counterfactual_search_pruned_states)
        for item in result.intervals
    )
    intervals_exhaustive = all(item.search_exhaustive is True for item in result.intervals)
    global_counters_valid = all(
        _valid_nonnegative_counter(value)
        for value in (
            main_pruned,
            counterfactual_pruned,
            result.search.pruned_states,
        )
    )
    if not interval_counters_valid or not global_counters_valid:
        return E0038ExactSearchOutcome(
            status=E0038ExactSearchStatus.ABSTAINED_NONZERO_PRUNING,
            reason=(
                "exact-policy search returned malformed pruning counters; "
                "mapping result was withheld"
            ),
            plan=plan,
            align_invocation_count=1,
            main_search_pruned_states=0,
            counterfactual_search_pruned_states=0,
            result=None,
        )
    interval_main = sum(item.main_search_pruned_states for item in result.intervals)
    interval_counterfactual = sum(
        item.counterfactual_search_pruned_states for item in result.intervals
    )
    pruning_consistent = (
        interval_counters_valid
        and global_counters_valid
        and intervals_exhaustive
        and main_pruned == interval_main
        and counterfactual_pruned == interval_counterfactual
        and result.search.pruned_states == main_pruned + counterfactual_pruned
    )
    zero_pruning = (
        pruning_consistent
        and main_pruned == 0
        and counterfactual_pruned == 0
        and all(
            item.main_search_pruned_states == 0 and item.counterfactual_search_pruned_states == 0
            for item in result.intervals
        )
    )
    if not zero_pruning:
        return E0038ExactSearchOutcome(
            status=E0038ExactSearchStatus.ABSTAINED_NONZERO_PRUNING,
            reason=(
                "exact-policy search did not produce a consistent zero-pruning "
                "certificate; mapping result was withheld"
            ),
            plan=plan,
            align_invocation_count=1,
            main_search_pruned_states=main_pruned,
            counterfactual_search_pruned_states=counterfactual_pruned,
            result=None,
        )

    return E0038ExactSearchOutcome(
        status=E0038ExactSearchStatus.EXACT_SEARCH_COMPLETE,
        reason=(
            "immutable ordered-subgraph v2 completed with interval identity parity and "
            "zero main/counterfactual pruning; mapping acceptance remains governed by "
            "the unchanged v2 gates"
        ),
        plan=plan,
        align_invocation_count=1,
        main_search_pruned_states=0,
        counterfactual_search_pruned_states=0,
        result=result,
    )
