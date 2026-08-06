from __future__ import annotations

from datetime import date

from bctc_ai.axes.header_binding import HeaderBinding
from bctc_ai.axes.period_propagation_v1 import (
    PeriodBindingMode,
    PeriodTableInput,
    ValueAxisPosition,
    load_period_propagation_policy,
    propagate_table_periods,
)
from bctc_ai.core.contracts import BoundingBox


def _binding(axis: str, raw: str, end: date, role: str, x0: float) -> HeaderBinding:
    return HeaderBinding(
        axis_id=axis,
        raw_header=raw,
        header_bbox=BoundingBox(x0, 10, x0 + 50, 30),
        unit="VND",
        unit_multiplier=1_000_000,
        unit_bbox=BoundingBox(400, 4, 480, 9),
        period_start=end,
        period_end=end,
        period_type="SNAPSHOT",
        duration_months=None,
        current_or_comparative=role,
        restated=False,
        confidence=1.0,
        evidence=("visible PDF header",),
    )


def _ctg_first() -> PeriodTableInput:
    return PeriodTableInput(
        table_id="ctg-cdkt-p3",
        page=3,
        table_order=0,
        statement_instance_id="ctg-2026q2-cdkt",
        statement_type="CDKT",
        scope="CONSOLIDATED",
        value_axes=(ValueAxisPosition("left", 0.72), ValueAxisPosition("right", 0.90)),
        local_bindings=(
            _binding("left", "Ngày 30 tháng 06 năm 2026", date(2026, 6, 30), "CURRENT", 500),
            _binding(
                "right",
                "Ngày 31 tháng 12 năm 2025 (Số kiểm toán)",
                date(2025, 12, 31),
                "COMPARATIVE",
                650,
            ),
        ),
    )


def _policy(project_root):
    return load_period_propagation_policy(project_root / "config/tables/period-propagation-v1.yaml")


def test_ctg_continuation_inherits_visible_header_orientation_by_column_order(project_root):
    first = _ctg_first()
    continuation = PeriodTableInput(
        table_id="ctg-cdkt-p4",
        page=4,
        table_order=0,
        statement_instance_id=first.statement_instance_id,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        value_axes=(ValueAxisPosition("p4-left", 0.721), ValueAxisPosition("p4-right", 0.899)),
        continuation_from_table_id=first.table_id,
    )
    result = propagate_table_periods(
        [first, continuation],
        accepted_continuations={(first.table_id, continuation.table_id)},
        policy=_policy(project_root),
    )
    assert not result.unresolved
    inherited = result.by_table_id()[continuation.table_id]
    assert inherited.binding_mode is PeriodBindingMode.INHERITED_ACCEPTED_CONTINUATION
    assert inherited.columns[0].current_or_comparative == "CURRENT"
    assert inherited.columns[0].period_end == date(2026, 6, 30)
    assert inherited.columns[1].current_or_comparative == "COMPARATIVE"
    assert inherited.columns[1].period_end == date(2025, 12, 31)
    assert inherited.columns[0].source_header_page == 3


def test_period_inheritance_stops_at_new_statement_or_changed_structure(project_root):
    first = _ctg_first()
    new_statement = PeriodTableInput(
        table_id="ctg-kqkd-p5",
        page=4,
        table_order=0,
        statement_instance_id="ctg-2026q2-kqkd",
        statement_type="KQKD",
        scope="CONSOLIDATED",
        value_axes=(ValueAxisPosition("left", 0.72), ValueAxisPosition("right", 0.90)),
        continuation_from_table_id=first.table_id,
        starts_new_statement=True,
    )
    result = propagate_table_periods(
        [first, new_statement],
        accepted_continuations={(first.table_id, new_statement.table_id)},
        policy=_policy(project_root),
    )
    assert new_statement.table_id not in result.by_table_id()
    assert result.unresolved[0].code == "PERIOD_INHERITANCE_BOUNDARY"


def test_partial_repeated_headers_fail_closed_instead_of_mixing_with_inheritance(project_root):
    first = _ctg_first()
    partial = PeriodTableInput(
        table_id="ctg-cdkt-p4",
        page=4,
        table_order=0,
        statement_instance_id=first.statement_instance_id,
        statement_type="CDKT",
        scope="CONSOLIDATED",
        value_axes=(ValueAxisPosition("left2", 0.72), ValueAxisPosition("right2", 0.90)),
        local_bindings=(_binding("left2", "30/06/2026", date(2026, 6, 30), "CURRENT", 500),),
        continuation_from_table_id=first.table_id,
    )
    result = propagate_table_periods(
        [first, partial],
        accepted_continuations={(first.table_id, partial.table_id)},
        policy=_policy(project_root),
    )
    assert partial.table_id not in result.by_table_id()
    assert result.unresolved[0].code == "PARTIAL_LOCAL_PERIOD_HEADERS"


def test_period_propagator_has_no_numeric_value_or_history_input():
    parameter_names = propagate_table_periods.__annotations__
    assert "values" not in parameter_names
    assert "mongodb" not in parameter_names
    assert "history" not in parameter_names
