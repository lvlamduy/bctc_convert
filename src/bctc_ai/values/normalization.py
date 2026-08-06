from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from bctc_ai.core.contracts import ObservationKind, ValueStatus
from bctc_ai.core.text import ParsedNumber, parse_financial_number


@dataclass(frozen=True)
class NormalizedFinancialCell:
    """Raw cell evidence plus its non-destructive numeric interpretation."""

    raw_value: str | None
    normalized_numeric_value: Decimal | None
    normalized_value: str | None
    observation: ObservationKind | None
    value_status: ValueStatus
    row_visible: bool
    cell_geometry_verified: bool
    table_structure_verified: bool
    reason: str


def _storage_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _visible_numeric_value(
    parsed: ParsedNumber,
    *,
    cell_geometry_verified: bool,
    table_structure_verified: bool,
) -> tuple[Decimal | None, str | None]:
    if parsed.observation in {ObservationKind.VALUE, ObservationKind.ZERO}:
        return parsed.value, None
    if parsed.observation in {ObservationKind.DASH, ObservationKind.BLANK}:
        if cell_geometry_verified and table_structure_verified:
            return Decimal(0), None
        return None, "dash/blank requires verified numeric-cell geometry and table structure"
    if parsed.observation is ObservationKind.NOT_APPLICABLE:
        return None, "not-applicable token has no financial numeric value"
    return None, parsed.reason or "invalid financial token"


def normalize_financial_cell(
    raw_value: str | None,
    *,
    row_visible: bool,
    cell_geometry_verified: bool,
    table_structure_verified: bool,
    target_template_in_scope: bool = True,
    mapping_ambiguous: bool = False,
    reference_available: bool = True,
) -> NormalizedFinancialCell:
    """Normalize a cell without conflating absence, zero, scope, or reference gaps.

    The function never infers row presence from a schema or historical value. A
    dash/blank becomes zero only after the row and numeric-cell structure have
    been observed. ``reference_available`` affects evaluation disposition only;
    it does not erase visible PDF evidence.
    """

    if not row_visible:
        if raw_value is not None and raw_value.strip():
            raise ValueError("an absent row cannot carry visible raw cell text")
        return NormalizedFinancialCell(
            raw_value=None,
            normalized_numeric_value=None,
            normalized_value=None,
            observation=None,
            value_status=ValueStatus.NOT_OBSERVED,
            row_visible=False,
            cell_geometry_verified=False,
            table_structure_verified=False,
            reason="schema row is not visibly present in the PDF",
        )

    parsed = parse_financial_number(raw_value)
    numeric, numeric_error = _visible_numeric_value(
        parsed,
        cell_geometry_verified=cell_geometry_verified,
        table_structure_verified=table_structure_verified,
    )

    if not target_template_in_scope:
        status = ValueStatus.OUT_OF_SCOPE_FOR_TARGET_TEMPLATE
        reason = "visible row belongs outside the requested target template"
    elif mapping_ambiguous or numeric_error is not None:
        status = ValueStatus.AMBIGUOUS_MAPPING
        reason = (
            "visible row does not yet support one schema ID"
            if mapping_ambiguous
            else numeric_error or "unresolved cell"
        )
    elif not reference_available:
        status = ValueStatus.REFERENCE_NOT_YET_BUILT
        reason = "machine reference is unavailable; visible extraction is retained"
    elif numeric == 0:
        status = ValueStatus.OBSERVED_ZERO
        reason = "visible numeric zero, dash, or verified empty numeric cell"
    else:
        status = ValueStatus.OBSERVED_VALUE
        reason = "visible non-zero financial value"

    return NormalizedFinancialCell(
        raw_value=raw_value,
        normalized_numeric_value=numeric,
        normalized_value=_storage_text(numeric),
        observation=parsed.observation,
        value_status=status,
        row_visible=True,
        cell_geometry_verified=cell_geometry_verified,
        table_structure_verified=table_structure_verified,
        reason=reason,
    )
