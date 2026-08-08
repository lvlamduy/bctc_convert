"""Coverage-driven KQKD item mapping over independent reader labels."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from bctc_ai.mapping.ordered_subgraph_v2 import (
    MappingRunStatus,
    OrderedSubgraphV2Error,
    OrderedSubgraphV2Policy,
    OrderedSubgraphV2Result,
    RowMappingStatus,
    SchemaProjectionV2,
    SourceRelationType,
    SourceRowRole,
    SourceStructureRowV2,
    align_ordered_subgraph_v2,
    build_schema_projection_v2,
    load_ordered_subgraph_v2_policy,
)
from bctc_ai.schema.registry import SchemaItem

KQKD_POLICY_RELATIVE_PATH = Path("config/mapping/kqkd-ordered-subgraph-v2.yaml")
KQKD_SCHEMA_ITEM_COUNT = 24
KQKD_TRAILING_AGGREGATE_IDS = (4385, 4386, 4390, 4376, 4377, 4382, 4378, 4380)

_MAX_SOURCE_ROWS = 256
_MAX_READERS = 16
_MAX_ROW_ID_LENGTH = 256
_MAX_READER_ID_LENGTH = 128
_MAX_LABEL_LENGTH = 4096
_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAPPING_INPUTS = (
    "KQKD_WORKBOOK_DISPLAY_ORDER",
    "KQKD_SCHEMA_HIERARCHY",
    "CANONICAL_AND_STRUCTURAL_ALIASES",
    "INDEPENDENT_READER_LABELS",
)


class KQKDItemMappingError(ValueError):
    """Raised when KQKD mapping evidence or reconciliation is malformed."""


class KQKDSchemaStatus(StrEnum):
    MAPPED = "MAPPED"
    NOT_OBSERVED_IN_THIS_PDF = "NOT_OBSERVED_IN_THIS_PDF"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


class KQKDSourceRowStatus(StrEnum):
    MAPPED = "MAPPED"
    SOURCE_ONLY_PDF_ROW = "SOURCE_ONLY_PDF_ROW"
    AMBIGUOUS_MAPPING = "AMBIGUOUS_MAPPING"


@dataclass(frozen=True)
class KQKDSchemaDisposition:
    report_norm_id: int
    display_order: int
    canonical_name: str
    status: str
    source_row_id: str | None
    candidate_source_row_ids: tuple[str, ...]
    ordered_subgraph_status: str
    reason: str


@dataclass(frozen=True)
class KQKDSourceDisposition:
    row_id: str
    order: int
    status: str
    report_norm_id: int | None
    candidate_report_norm_ids: tuple[int, ...]
    ordered_subgraph_status: str
    reason: str


@dataclass(frozen=True)
class KQKDItemMappingResult:
    statement_type: str
    status: str
    automatic_selection_allowed: bool
    schema_item_count: int
    mapped_schema_count: int
    not_observed_schema_count: int
    ambiguous_schema_count: int
    source_row_count: int
    mapped_source_row_count: int
    source_only_row_count: int
    ambiguous_source_row_count: int
    schema_dispositions: tuple[KQKDSchemaDisposition, ...]
    source_dispositions: tuple[KQKDSourceDisposition, ...]
    schema_projection_sha256: str
    policy_sha256: str
    mapping_inputs: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_kqkd_mapping_policy(path: Path) -> OrderedSubgraphV2Policy:
    """Load the common v2 policy and enforce its KQKD roll-up exceptions."""

    try:
        policy = load_ordered_subgraph_v2_policy(path)
    except (OSError, OrderedSubgraphV2Error) as exc:
        raise KQKDItemMappingError(f"cannot load KQKD mapping policy: {path}") from exc
    if policy.trailing_aggregate_ids != KQKD_TRAILING_AGGREGATE_IDS:
        raise KQKDItemMappingError("KQKD trailing aggregate policy drifted")
    return policy


def build_kqkd_schema_projection(schema: Sequence[SchemaItem]) -> SchemaProjectionV2:
    """Build the 24-item history-free KQKD projection from workbook hierarchy."""

    try:
        projection = build_schema_projection_v2(schema, "KQKD")
    except OrderedSubgraphV2Error as exc:
        raise KQKDItemMappingError("cannot build KQKD schema projection") from exc
    if len(projection.nodes) != KQKD_SCHEMA_ITEM_COUNT:
        raise KQKDItemMappingError("KQKD projection must contain exactly 24 schema items")
    if tuple(node.display_order for node in projection.nodes) != tuple(
        range(KQKD_SCHEMA_ITEM_COUNT)
    ):
        raise KQKDItemMappingError("KQKD workbook display order is not contiguous")

    by_id = projection.by_id()
    aggregate_ids = {node.report_norm_id for node in projection.nodes if node.child_report_norm_ids}
    if aggregate_ids != set(KQKD_TRAILING_AGGREGATE_IDS):
        raise KQKDItemMappingError("KQKD hierarchy aggregate inventory drifted")
    for aggregate_id in KQKD_TRAILING_AGGREGATE_IDS:
        aggregate = by_id[aggregate_id]
        if any(
            by_id[child_id].display_order >= aggregate.display_order
            for child_id in aggregate.child_report_norm_ids
        ):
            raise KQKDItemMappingError("KQKD aggregate is not displayed after all of its children")
    return projection


def _identity_field(value: object, field: str) -> object:
    if isinstance(value, Mapping):
        return value.get(field)
    return getattr(value, field, None)


def adapt_kqkd_logical_rows(
    logical_rows: Sequence[object],
    *,
    labels_by_reader: Mapping[str, Mapping[str, str]],
    report_scope: str = "UNKNOWN",
) -> tuple[SourceStructureRowV2, ...]:
    """Adapt parser models or raw row dictionaries without opening their cell payloads.

    ``labels_by_reader`` is reader-major: each reader maps parser ``row_id`` to
    its independently produced label. Only row identity, order, scope, and these
    label mappings cross into the ordered-subgraph mapper.
    """

    if isinstance(logical_rows, (str, bytes)) or not isinstance(logical_rows, Sequence):
        raise KQKDItemMappingError("KQKD logical rows must be a sequence")
    frozen_rows = tuple(logical_rows)
    if not frozen_rows or len(frozen_rows) > _MAX_SOURCE_ROWS:
        raise KQKDItemMappingError("KQKD logical row count is invalid")
    if not isinstance(labels_by_reader, Mapping) or not labels_by_reader:
        raise KQKDItemMappingError("KQKD independent reader labels are absent")
    if len(labels_by_reader) > _MAX_READERS:
        raise KQKDItemMappingError("KQKD reader count exceeds the bound")
    scope = str(report_scope).upper()
    if scope not in {"UNKNOWN", "CONSOLIDATED", "SEPARATE"}:
        raise KQKDItemMappingError("KQKD report scope is invalid")

    identities: list[tuple[str, int]] = []
    for raw in frozen_rows:
        row_id = _identity_field(raw, "row_id")
        order = _identity_field(raw, "order")
        ordinal = _identity_field(raw, "ordinal")
        if order is None:
            order = ordinal
        elif ordinal is not None and order != ordinal:
            raise KQKDItemMappingError("KQKD row order and ordinal disagree")
        if (
            not isinstance(row_id, str)
            or not row_id
            or len(row_id) > _MAX_ROW_ID_LENGTH
            or isinstance(order, bool)
            or not isinstance(order, int)
            or order < 0
        ):
            raise KQKDItemMappingError("KQKD row identity or order is invalid")
        identities.append((row_id, order))
    row_ids = {row_id for row_id, _order in identities}
    if len(row_ids) != len(identities) or len({order for _row_id, order in identities}) != len(
        identities
    ):
        raise KQKDItemMappingError("KQKD row IDs and order values must be unique")

    frozen_labels: dict[str, dict[str, str]] = {}
    for reader_id, proposals in labels_by_reader.items():
        if (
            not isinstance(reader_id, str)
            or not reader_id
            or len(reader_id) > _MAX_READER_ID_LENGTH
            or not isinstance(proposals, Mapping)
        ):
            raise KQKDItemMappingError("KQKD reader label mapping is invalid")
        unknown = set(proposals) - row_ids
        if unknown:
            raise KQKDItemMappingError("KQKD reader labels reference an unknown row")
        normalized: dict[str, str] = {}
        for row_id, label in proposals.items():
            if not isinstance(row_id, str) or not isinstance(label, str):
                raise KQKDItemMappingError("KQKD reader proposal is not text")
            if len(label) > _MAX_LABEL_LENGTH:
                raise KQKDItemMappingError("KQKD reader proposal exceeds the length bound")
            normalized[row_id] = label
        frozen_labels[reader_id] = normalized

    return tuple(
        SourceStructureRowV2(
            row_id=row_id,
            order=order,
            labels_by_reader={
                reader_id: frozen_labels[reader_id].get(row_id, "")
                for reader_id in sorted(frozen_labels)
            },
            row_role=SourceRowRole.UNKNOWN.value,
            parent_row_id=None,
            relation_type=SourceRelationType.UNKNOWN.value,
            report_scope=scope,
            target_template_in_scope=True,
        )
        for row_id, order in identities
    )


def _schema_status(
    core_status: str, selected_row: str | None, has_candidates: bool, *, ambiguous: bool
) -> str:
    if selected_row is not None:
        return KQKDSchemaStatus.MAPPED.value
    if core_status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value or (
        ambiguous and has_candidates
    ):
        return KQKDSchemaStatus.AMBIGUOUS_MAPPING.value
    return KQKDSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value


def _source_status(
    core_status: str, selected_id: int | None, has_candidates: bool, *, ambiguous: bool
) -> str:
    if selected_id is not None:
        return KQKDSourceRowStatus.MAPPED.value
    if core_status == RowMappingStatus.AMBIGUOUS_ACROSS_PATHS.value or (
        ambiguous and has_candidates
    ):
        return KQKDSourceRowStatus.AMBIGUOUS_MAPPING.value
    return KQKDSourceRowStatus.SOURCE_ONLY_PDF_ROW.value


def _reconcile(
    core: OrderedSubgraphV2Result,
    projection: SchemaProjectionV2,
    source_rows: tuple[SourceStructureRowV2, ...],
) -> KQKDItemMappingResult:
    ambiguous = core.status is MappingRunStatus.AMBIGUOUS_MAPPING
    node_by_id = projection.by_id()
    order_by_row = {row.row_id: row.order for row in source_rows}
    schema_dispositions = tuple(
        KQKDSchemaDisposition(
            report_norm_id=item.report_norm_id,
            display_order=node_by_id[item.report_norm_id].display_order,
            canonical_name=node_by_id[item.report_norm_id].canonical_name,
            status=_schema_status(
                item.status,
                item.selected_row_id,
                bool(item.candidate_row_ids),
                ambiguous=ambiguous,
            ),
            source_row_id=item.selected_row_id,
            candidate_source_row_ids=tuple(item.candidate_row_ids),
            ordered_subgraph_status=item.status,
            reason=item.reason,
        )
        for item in core.schema_dispositions
    )
    source_dispositions = tuple(
        KQKDSourceDisposition(
            row_id=item.row_id,
            order=order_by_row[item.row_id],
            status=_source_status(
                item.status,
                item.selected_report_norm_id,
                bool(item.candidate_report_norm_ids),
                ambiguous=ambiguous,
            ),
            report_norm_id=item.selected_report_norm_id,
            candidate_report_norm_ids=tuple(item.candidate_report_norm_ids),
            ordered_subgraph_status=item.status,
            reason=item.reason,
        )
        for item in core.row_mappings
    )
    result = KQKDItemMappingResult(
        statement_type="KQKD",
        status=str(core.status),
        automatic_selection_allowed=core.automatic_selection_allowed,
        schema_item_count=len(schema_dispositions),
        mapped_schema_count=sum(
            item.status == KQKDSchemaStatus.MAPPED.value for item in schema_dispositions
        ),
        not_observed_schema_count=sum(
            item.status == KQKDSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            for item in schema_dispositions
        ),
        ambiguous_schema_count=sum(
            item.status == KQKDSchemaStatus.AMBIGUOUS_MAPPING.value for item in schema_dispositions
        ),
        source_row_count=len(source_dispositions),
        mapped_source_row_count=sum(
            item.status == KQKDSourceRowStatus.MAPPED.value for item in source_dispositions
        ),
        source_only_row_count=sum(
            item.status == KQKDSourceRowStatus.SOURCE_ONLY_PDF_ROW.value
            for item in source_dispositions
        ),
        ambiguous_source_row_count=sum(
            item.status == KQKDSourceRowStatus.AMBIGUOUS_MAPPING.value
            for item in source_dispositions
        ),
        schema_dispositions=schema_dispositions,
        source_dispositions=source_dispositions,
        schema_projection_sha256=core.schema_projection_sha256,
        policy_sha256=core.policy_sha256,
        mapping_inputs=_MAPPING_INPUTS,
        reason=core.reason,
    )
    validate_kqkd_mapping_result(result)
    return result


def reconcile_kqkd_source_rows(
    source_rows: Sequence[SourceStructureRowV2],
    *,
    schema: Sequence[SchemaItem],
    policy: OrderedSubgraphV2Policy,
) -> KQKDItemMappingResult:
    """Run ordered-subgraph v2 and reconcile every KQKD schema item and source row."""

    frozen_rows = tuple(source_rows)
    if (
        not frozen_rows
        or len(frozen_rows) > _MAX_SOURCE_ROWS
        or any(not isinstance(row, SourceStructureRowV2) for row in frozen_rows)
    ):
        raise KQKDItemMappingError("KQKD source rows are invalid")
    projection = build_kqkd_schema_projection(schema)
    if policy.trailing_aggregate_ids != KQKD_TRAILING_AGGREGATE_IDS:
        raise KQKDItemMappingError("KQKD mapping policy has incomplete roll-up exceptions")
    try:
        core = align_ordered_subgraph_v2(frozen_rows, projection, policy=policy)
    except OrderedSubgraphV2Error as exc:
        raise KQKDItemMappingError("KQKD ordered-subgraph mapping failed") from exc
    return _reconcile(core, projection, frozen_rows)


def map_kqkd_items(
    logical_rows: Sequence[object],
    *,
    labels_by_reader: Mapping[str, Mapping[str, str]],
    schema: Sequence[SchemaItem],
    policy: OrderedSubgraphV2Policy,
    report_scope: str = "UNKNOWN",
) -> KQKDItemMappingResult:
    """Map parser rows using only independent reader labels and KQKD structure."""

    source_rows = adapt_kqkd_logical_rows(
        logical_rows,
        labels_by_reader=labels_by_reader,
        report_scope=report_scope,
    )
    return reconcile_kqkd_source_rows(source_rows, schema=schema, policy=policy)


def map_kqkd_logical_rows(
    logical_rows: Sequence[object],
    *,
    labels_by_reader: Mapping[str, Mapping[str, str]],
    schema: Sequence[SchemaItem],
    policy: OrderedSubgraphV2Policy,
    report_scope: str = "UNKNOWN",
) -> KQKDItemMappingResult:
    """Named adapter for callers passing ``KQKDLogicalRow`` parser models."""

    return map_kqkd_items(
        logical_rows,
        labels_by_reader=labels_by_reader,
        schema=schema,
        policy=policy,
        report_scope=report_scope,
    )


def _record(value: object, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise KQKDItemMappingError(f"{label} keyset is invalid")
    return value


def _sequence(value: object, label: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise KQKDItemMappingError(f"{label} must be a sequence")
    return tuple(value)


def validate_kqkd_mapping_result(
    value: KQKDItemMappingResult | Mapping[str, Any],
) -> KQKDItemMappingResult | Mapping[str, Any]:
    """Validate model or raw-dictionary reconciliation output and all cross-links."""

    raw = value.to_dict() if isinstance(value, KQKDItemMappingResult) else value
    result = _record(
        raw,
        {
            "statement_type",
            "status",
            "automatic_selection_allowed",
            "schema_item_count",
            "mapped_schema_count",
            "not_observed_schema_count",
            "ambiguous_schema_count",
            "source_row_count",
            "mapped_source_row_count",
            "source_only_row_count",
            "ambiguous_source_row_count",
            "schema_dispositions",
            "source_dispositions",
            "schema_projection_sha256",
            "policy_sha256",
            "mapping_inputs",
            "reason",
        },
        "KQKD mapping result",
    )
    if (
        result.get("statement_type") != "KQKD"
        or result.get("status") not in {item.value for item in MappingRunStatus}
        or result.get("automatic_selection_allowed")
        is not (result.get("status") == MappingRunStatus.RESOLVED.value)
        or result.get("schema_item_count") != KQKD_SCHEMA_ITEM_COUNT
        or _SHA256.fullmatch(str(result.get("schema_projection_sha256", ""))) is None
        or _SHA256.fullmatch(str(result.get("policy_sha256", ""))) is None
        or tuple(_sequence(result.get("mapping_inputs"), "KQKD mapping inputs")) != _MAPPING_INPUTS
        or not isinstance(result.get("reason"), str)
        or not result["reason"]
    ):
        raise KQKDItemMappingError("KQKD mapping result identity is invalid")

    raw_schema = _sequence(result.get("schema_dispositions"), "KQKD schema dispositions")
    raw_source = _sequence(result.get("source_dispositions"), "KQKD source dispositions")
    if len(raw_schema) != KQKD_SCHEMA_ITEM_COUNT or not raw_source:
        raise KQKDItemMappingError("KQKD reconciliation coverage is incomplete")
    schema_records = tuple(
        _record(
            item,
            {
                "report_norm_id",
                "display_order",
                "canonical_name",
                "status",
                "source_row_id",
                "candidate_source_row_ids",
                "ordered_subgraph_status",
                "reason",
            },
            "KQKD schema disposition",
        )
        for item in raw_schema
    )
    source_records = tuple(
        _record(
            item,
            {
                "row_id",
                "order",
                "status",
                "report_norm_id",
                "candidate_report_norm_ids",
                "ordered_subgraph_status",
                "reason",
            },
            "KQKD source disposition",
        )
        for item in raw_source
    )

    schema_ids: set[int] = set()
    schema_orders: list[int] = []
    schema_by_id: dict[int, Mapping[str, Any]] = {}
    schema_statuses = {item.value for item in KQKDSchemaStatus}
    for item in schema_records:
        report_norm_id = item.get("report_norm_id")
        display_order = item.get("display_order")
        candidates = _sequence(item.get("candidate_source_row_ids"), "schema candidate rows")
        if (
            isinstance(report_norm_id, bool)
            or not isinstance(report_norm_id, int)
            or report_norm_id <= 0
            or isinstance(display_order, bool)
            or not isinstance(display_order, int)
            or item.get("status") not in schema_statuses
            or not isinstance(item.get("canonical_name"), str)
            or not item["canonical_name"]
            or any(not isinstance(candidate, str) or not candidate for candidate in candidates)
            or len(candidates) != len(set(candidates))
            or not isinstance(item.get("ordered_subgraph_status"), str)
            or not item["ordered_subgraph_status"]
            or not isinstance(item.get("reason"), str)
            or not item["reason"]
        ):
            raise KQKDItemMappingError("KQKD schema disposition is invalid")
        selected_row = item.get("source_row_id")
        if (item["status"] == KQKDSchemaStatus.MAPPED.value) != isinstance(selected_row, str):
            raise KQKDItemMappingError("KQKD mapped schema/source linkage is invalid")
        schema_ids.add(report_norm_id)
        schema_orders.append(display_order)
        schema_by_id[report_norm_id] = item
    if len(schema_ids) != KQKD_SCHEMA_ITEM_COUNT or schema_orders != list(
        range(KQKD_SCHEMA_ITEM_COUNT)
    ):
        raise KQKDItemMappingError("KQKD schema IDs or workbook order are not unique")

    source_ids: set[str] = set()
    source_orders: list[int] = []
    source_by_id: dict[str, Mapping[str, Any]] = {}
    source_statuses = {item.value for item in KQKDSourceRowStatus}
    for item in source_records:
        row_id = item.get("row_id")
        order = item.get("order")
        candidates = _sequence(item.get("candidate_report_norm_ids"), "source candidate IDs")
        if (
            not isinstance(row_id, str)
            or not row_id
            or isinstance(order, bool)
            or not isinstance(order, int)
            or item.get("status") not in source_statuses
            or any(
                isinstance(candidate, bool)
                or not isinstance(candidate, int)
                or candidate not in schema_ids
                for candidate in candidates
            )
            or len(candidates) != len(set(candidates))
            or not isinstance(item.get("ordered_subgraph_status"), str)
            or not item["ordered_subgraph_status"]
            or not isinstance(item.get("reason"), str)
            or not item["reason"]
        ):
            raise KQKDItemMappingError("KQKD source disposition is invalid")
        selected_id = item.get("report_norm_id")
        if (item["status"] == KQKDSourceRowStatus.MAPPED.value) != (
            isinstance(selected_id, int) and not isinstance(selected_id, bool)
        ):
            raise KQKDItemMappingError("KQKD source/schema linkage is invalid")
        source_ids.add(row_id)
        source_orders.append(order)
        source_by_id[row_id] = item
    if len(source_ids) != len(source_records) or source_orders != sorted(set(source_orders)):
        raise KQKDItemMappingError("KQKD source row IDs or order are not unique")

    for schema_id, item in schema_by_id.items():
        candidate_rows = _sequence(item["candidate_source_row_ids"], "schema candidate rows")
        if any(row_id not in source_ids for row_id in candidate_rows):
            raise KQKDItemMappingError("KQKD schema candidate references an unknown source row")
        selected_row = item.get("source_row_id")
        if selected_row is not None:
            source = source_by_id.get(selected_row)
            if source is None or source.get("report_norm_id") != schema_id:
                raise KQKDItemMappingError("KQKD schema/source selection is not bijective")
    for row_id, item in source_by_id.items():
        selected_id = item.get("report_norm_id")
        if selected_id is not None and schema_by_id[selected_id].get("source_row_id") != row_id:
            raise KQKDItemMappingError("KQKD source/schema selection is not bijective")

    expected_counts = {
        "mapped_schema_count": sum(
            item["status"] == KQKDSchemaStatus.MAPPED.value for item in schema_records
        ),
        "not_observed_schema_count": sum(
            item["status"] == KQKDSchemaStatus.NOT_OBSERVED_IN_THIS_PDF.value
            for item in schema_records
        ),
        "ambiguous_schema_count": sum(
            item["status"] == KQKDSchemaStatus.AMBIGUOUS_MAPPING.value for item in schema_records
        ),
        "source_row_count": len(source_records),
        "mapped_source_row_count": sum(
            item["status"] == KQKDSourceRowStatus.MAPPED.value for item in source_records
        ),
        "source_only_row_count": sum(
            item["status"] == KQKDSourceRowStatus.SOURCE_ONLY_PDF_ROW.value
            for item in source_records
        ),
        "ambiguous_source_row_count": sum(
            item["status"] == KQKDSourceRowStatus.AMBIGUOUS_MAPPING.value for item in source_records
        ),
    }
    if any(result.get(name) != count for name, count in expected_counts.items()):
        raise KQKDItemMappingError("KQKD reconciliation counts drifted")
    return value


__all__ = [
    "KQKDItemMappingError",
    "KQKDItemMappingResult",
    "KQKDSchemaDisposition",
    "KQKDSchemaStatus",
    "KQKDSourceDisposition",
    "KQKDSourceRowStatus",
    "KQKD_POLICY_RELATIVE_PATH",
    "KQKD_SCHEMA_ITEM_COUNT",
    "KQKD_TRAILING_AGGREGATE_IDS",
    "adapt_kqkd_logical_rows",
    "build_kqkd_schema_projection",
    "load_kqkd_mapping_policy",
    "map_kqkd_items",
    "map_kqkd_logical_rows",
    "reconcile_kqkd_source_rows",
    "validate_kqkd_mapping_result",
]
