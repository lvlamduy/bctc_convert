from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.core.contracts import BoundingBox


class PeriodBindingMode(StrEnum):
    LOCAL_VISIBLE_HEADERS = "LOCAL_VISIBLE_HEADERS"
    INHERITED_ACCEPTED_CONTINUATION = "INHERITED_ACCEPTED_CONTINUATION"


@dataclass(frozen=True)
class PeriodPropagationPolicy:
    version: int
    mode: str
    maximum_center_drift: float
    source_path: Path


@dataclass(frozen=True)
class ValueAxisPosition:
    axis_id: str
    center_ratio: float

    def __post_init__(self) -> None:
        if not self.axis_id:
            raise ValueError("value axis requires an ID")
        if not 0 <= self.center_ratio <= 1:
            raise ValueError("value-axis center_ratio must be normalized to [0, 1]")


@dataclass(frozen=True)
class PeriodTableInput:
    table_id: str
    page: int
    table_order: int
    statement_instance_id: str
    statement_type: str
    scope: str
    value_axes: tuple[ValueAxisPosition, ...]
    local_bindings: tuple[HeaderBinding, ...] = ()
    continuation_from_table_id: str | None = None
    starts_new_statement: bool = False
    starts_new_table: bool = False
    explicit_period_structure_change: bool = False

    def __post_init__(self) -> None:
        if not self.table_id or not self.statement_instance_id or not self.statement_type:
            raise ValueError("period table requires table and statement identities")
        if self.page < 1 or self.table_order < 0:
            raise ValueError("invalid table document position")
        if not self.value_axes:
            raise ValueError("period table requires at least one numeric value axis")
        axis_ids = [axis.axis_id for axis in self.value_axes]
        if len(axis_ids) != len(set(axis_ids)):
            raise ValueError(f"duplicate value-axis IDs in {self.table_id}")
        centers = [axis.center_ratio for axis in self.value_axes]
        if centers != sorted(centers) or len(centers) != len(set(centers)):
            raise ValueError(
                f"value axes must be unique and ordered left-to-right in {self.table_id}"
            )


@dataclass(frozen=True)
class PeriodColumn:
    ordinal: int
    axis_id: str
    center_ratio: float
    period_start: date | None
    period_end: date
    period_type: str
    current_or_comparative: str
    raw_header: str
    header_bbox: BoundingBox
    unit: str | None
    unit_multiplier: int | None
    source_header_table_id: str
    source_header_page: int
    source_header_axis_id: str


@dataclass(frozen=True)
class TablePeriodMap:
    table_id: str
    page: int
    statement_instance_id: str
    statement_type: str
    scope: str
    columns: tuple[PeriodColumn, ...]
    binding_mode: PeriodBindingMode
    inherited_from_table_id: str | None
    inheritance_depth: int
    evidence: tuple[str, ...]

    def column_for_role(self, role: str) -> tuple[PeriodColumn, ...]:
        return tuple(column for column in self.columns if column.current_or_comparative == role)


@dataclass(frozen=True)
class PeriodPropagationIssue:
    table_id: str
    page: int
    code: str
    reason: str


@dataclass(frozen=True)
class PeriodPropagationResult:
    table_maps: tuple[TablePeriodMap, ...]
    unresolved: tuple[PeriodPropagationIssue, ...]

    def by_table_id(self) -> dict[str, TablePeriodMap]:
        return {table.table_id: table for table in self.table_maps}


def load_period_propagation_policy(path: Path) -> PeriodPropagationPolicy:
    payload: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    requirements = payload.get("requirements")
    stops = payload.get("stops")
    safety = payload.get("safety")
    if (
        payload.get("version") != 1
        or payload.get("mode") != "TABLE_LEVEL_VISIBLE_HEADER_INHERITANCE"
        or not isinstance(requirements, dict)
        or not isinstance(stops, dict)
        or not isinstance(safety, dict)
    ):
        raise ValueError(f"invalid period propagation v1 identity: {path}")
    required_true = (
        "accepted_continuation_edge",
        "adjacent_pdf_pages",
        "same_statement_instance",
        "same_statement_type",
        "same_scope",
        "compatible_value_axis_count_order_geometry",
        "complete_local_header_set_or_no_local_period_evidence",
    )
    stop_true = (
        "new_statement",
        "new_non_continuation_table",
        "explicit_period_structure_change",
    )
    safety_false = (
        "numeric_values_are_inputs",
        "historical_values_are_inputs",
        "numeric_magnitude_can_assign_period",
        "left_right_alone_can_assign_role",
    )
    if (
        any(requirements.get(name) is not True for name in required_true)
        or any(stops.get(name) is not True for name in stop_true)
        or any(safety.get(name) is not False for name in safety_false)
    ):
        raise ValueError(f"period propagation policy weakens a safety gate: {path}")
    maximum_center_drift = float(payload.get("maximum_value_axis_center_drift_ratio", -1))
    if not 0 <= maximum_center_drift <= 0.25:
        raise ValueError(f"invalid value-axis center drift threshold: {path}")
    return PeriodPropagationPolicy(
        version=1,
        mode=str(payload["mode"]),
        maximum_center_drift=maximum_center_drift,
        source_path=path.resolve(),
    )


def _has_any_local_period_evidence(bindings: tuple[HeaderBinding, ...]) -> bool:
    return any(
        binding.raw_header
        or binding.period_end is not None
        or binding.current_or_comparative is not None
        for binding in bindings
    )


def _local_period_map(table: PeriodTableInput) -> tuple[TablePeriodMap | None, str | None]:
    by_axis = {binding.axis_id: binding for binding in table.local_bindings}
    expected = {axis.axis_id for axis in table.value_axes}
    if set(by_axis) != expected:
        return None, "local header bindings do not cover exactly the numeric value axes"
    columns: list[PeriodColumn] = []
    for ordinal, axis in enumerate(table.value_axes):
        binding = by_axis[axis.axis_id]
        if (
            binding.period_end is None
            or binding.period_type is None
            or binding.current_or_comparative not in {"CURRENT", "COMPARATIVE"}
            or not binding.raw_header
            or binding.header_bbox is None
        ):
            return None, "local period header is partial or lacks visible-header provenance"
        columns.append(
            PeriodColumn(
                ordinal=ordinal,
                axis_id=axis.axis_id,
                center_ratio=axis.center_ratio,
                period_start=binding.period_start,
                period_end=binding.period_end,
                period_type=binding.period_type,
                current_or_comparative=binding.current_or_comparative,
                raw_header=binding.raw_header,
                header_bbox=binding.header_bbox,
                unit=binding.unit,
                unit_multiplier=binding.unit_multiplier,
                source_header_table_id=table.table_id,
                source_header_page=table.page,
                source_header_axis_id=axis.axis_id,
            )
        )
    return (
        TablePeriodMap(
            table_id=table.table_id,
            page=table.page,
            statement_instance_id=table.statement_instance_id,
            statement_type=table.statement_type,
            scope=table.scope,
            columns=tuple(columns),
            binding_mode=PeriodBindingMode.LOCAL_VISIBLE_HEADERS,
            inherited_from_table_id=None,
            inheritance_depth=0,
            evidence=(
                "periods bound to visible headers at table level",
                "left/right positions did not determine current/comparative roles",
            ),
        ),
        None,
    )


def _axis_layout_compatible(
    previous: TablePeriodMap,
    following: PeriodTableInput,
    *,
    maximum_center_drift: float,
) -> bool:
    if len(previous.columns) != len(following.value_axes):
        return False
    return all(
        abs(old.center_ratio - new.center_ratio) <= maximum_center_drift
        for old, new in zip(previous.columns, following.value_axes, strict=True)
    )


def _inherit_period_map(
    table: PeriodTableInput,
    previous: TablePeriodMap,
) -> TablePeriodMap:
    columns = tuple(
        PeriodColumn(
            ordinal=old.ordinal,
            axis_id=new.axis_id,
            center_ratio=new.center_ratio,
            period_start=old.period_start,
            period_end=old.period_end,
            period_type=old.period_type,
            current_or_comparative=old.current_or_comparative,
            raw_header=old.raw_header,
            header_bbox=old.header_bbox,
            unit=old.unit,
            unit_multiplier=old.unit_multiplier,
            source_header_table_id=old.source_header_table_id,
            source_header_page=old.source_header_page,
            source_header_axis_id=old.source_header_axis_id,
        )
        for old, new in zip(previous.columns, table.value_axes, strict=True)
    )
    return TablePeriodMap(
        table_id=table.table_id,
        page=table.page,
        statement_instance_id=table.statement_instance_id,
        statement_type=table.statement_type,
        scope=table.scope,
        columns=columns,
        binding_mode=PeriodBindingMode.INHERITED_ACCEPTED_CONTINUATION,
        inherited_from_table_id=previous.table_id,
        inheritance_depth=previous.inheritance_depth + 1,
        evidence=(
            "period map inherited through an accepted adjacent continuation edge",
            f"visible source headers remain on page {columns[0].source_header_page}",
            "numeric magnitudes and historical values were not inputs",
        ),
    )


def propagate_table_periods(
    tables: list[PeriodTableInput],
    *,
    accepted_continuations: set[tuple[str, str]],
    policy: PeriodPropagationPolicy,
) -> PeriodPropagationResult:
    """Propagate period axes only through verified continuation relationships."""

    identifiers = [table.table_id for table in tables]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate period table IDs")

    maps: dict[str, TablePeriodMap] = {}
    issues: list[PeriodPropagationIssue] = []
    ordered = sorted(tables, key=lambda table: (table.page, table.table_order, table.table_id))
    for table in ordered:
        has_local_evidence = _has_any_local_period_evidence(table.local_bindings)
        if has_local_evidence:
            local, error = _local_period_map(table)
            if local is None:
                issues.append(
                    PeriodPropagationIssue(
                        table.table_id,
                        table.page,
                        "PARTIAL_LOCAL_PERIOD_HEADERS",
                        error or "invalid local period headers",
                    )
                )
            else:
                maps[table.table_id] = local
            continue

        boundary_reasons = []
        if table.starts_new_statement:
            boundary_reasons.append("a new statement begins")
        if table.starts_new_table:
            boundary_reasons.append("a new non-continuation table begins")
        if table.explicit_period_structure_change:
            boundary_reasons.append("a different reporting-period structure is visible")
        if boundary_reasons:
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "PERIOD_INHERITANCE_BOUNDARY",
                    "; ".join(boundary_reasons),
                )
            )
            continue

        predecessor_id = table.continuation_from_table_id
        edge = (predecessor_id, table.table_id) if predecessor_id else None
        if predecessor_id is None or edge not in accepted_continuations:
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "NO_ACCEPTED_CONTINUATION",
                    "missing local headers and no accepted continuation predecessor",
                )
            )
            continue
        previous = maps.get(predecessor_id)
        if previous is None:
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "PREDECESSOR_PERIOD_UNRESOLVED",
                    f"predecessor {predecessor_id} has no resolved period map",
                )
            )
            continue
        if table.page != previous.page + 1:
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "NON_ADJACENT_CONTINUATION",
                    "period inheritance requires adjacent PDF pages",
                )
            )
            continue
        if (
            table.statement_instance_id != previous.statement_instance_id
            or table.statement_type != previous.statement_type
            or table.scope != previous.scope
        ):
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "STATEMENT_CONTEXT_CHANGED",
                    "statement instance, type, or scope differs from predecessor",
                )
            )
            continue
        if not _axis_layout_compatible(
            previous,
            table,
            maximum_center_drift=policy.maximum_center_drift,
        ):
            issues.append(
                PeriodPropagationIssue(
                    table.table_id,
                    table.page,
                    "VALUE_AXIS_LAYOUT_CHANGED",
                    "numeric column count/order/geometry is incompatible with predecessor",
                )
            )
            continue
        maps[table.table_id] = _inherit_period_map(table, previous)

    return PeriodPropagationResult(
        table_maps=tuple(maps[table.table_id] for table in ordered if table.table_id in maps),
        unresolved=tuple(issues),
    )
