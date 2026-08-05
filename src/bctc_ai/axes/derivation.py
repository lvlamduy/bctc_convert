from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from bctc_ai.core.contracts import EvidenceStatus


class PeriodDerivationError(ValueError):
    pass


@dataclass(frozen=True)
class PeriodValue:
    record_id: str
    document_id: str
    schema_id: int
    statement_type: str
    value: Decimal | None
    period_start: date
    period_end: date
    period_type: str
    scope: str
    unit: str
    accounting_basis: str
    status: EvidenceStatus
    page: int
    cell_id: str
    source_visible: bool


@dataclass(frozen=True)
class DerivedPeriodValue:
    schema_id: int
    statement_type: str
    value: Decimal
    period_start: date
    period_end: date
    period_type: str
    scope: str
    unit: str
    accounting_basis: str
    formula: str
    operand_record_ids: tuple[str, str]
    operand_document_ids: tuple[str, str]
    operand_pages: tuple[int, int]
    operand_cells: tuple[str, str]
    status: EvidenceStatus
    directly_observed: bool = False


def _quarter_number(value: date) -> int | None:
    if (value.month, value.day) == (3, 31):
        return 1
    if (value.month, value.day) == (6, 30):
        return 2
    if (value.month, value.day) == (9, 30):
        return 3
    if (value.month, value.day) == (12, 31):
        return 4
    return None


def derive_quarter_from_ytd(current_ytd: PeriodValue, prior_ytd: PeriodValue) -> DerivedPeriodValue:
    if current_ytd.value is None or prior_ytd.value is None:
        raise PeriodDerivationError("both visible YTD operands require numeric values")
    if not current_ytd.source_visible or not prior_ytd.source_visible:
        raise PeriodDerivationError("both YTD operands must be visible PDF cells")
    if current_ytd.period_type != "YTD" or prior_ytd.period_type != "YTD":
        raise PeriodDerivationError("period derivation accepts YTD operands only")
    equality_fields = (
        "schema_id",
        "statement_type",
        "scope",
        "unit",
        "accounting_basis",
        "period_start",
    )
    mismatches = [
        field
        for field in equality_fields
        if getattr(current_ytd, field) != getattr(prior_ytd, field)
    ]
    if mismatches:
        raise PeriodDerivationError(f"operand evidence mismatch: {', '.join(mismatches)}")
    current_quarter = _quarter_number(current_ytd.period_end)
    prior_quarter = _quarter_number(prior_ytd.period_end)
    if (
        current_quarter is None
        or prior_quarter is None
        or current_ytd.period_end.year != prior_ytd.period_end.year
        or current_quarter != prior_quarter + 1
    ):
        raise PeriodDerivationError("YTD operands must end on adjacent quarter boundaries")
    if current_ytd.period_start != date(current_ytd.period_end.year, 1, 1):
        raise PeriodDerivationError("YTD operands must begin on the first day of the year")
    permitted = {
        EvidenceStatus.AUTO_VERIFIED_HIGH,
        EvidenceStatus.AUTO_VERIFIED_MEDIUM,
    }
    if current_ytd.status not in permitted or prior_ytd.status not in permitted:
        raise PeriodDerivationError("both operands must already be accepted PDF observations")
    derived_start = prior_ytd.period_end + timedelta(days=1)
    return DerivedPeriodValue(
        schema_id=current_ytd.schema_id,
        statement_type=current_ytd.statement_type,
        value=current_ytd.value - prior_ytd.value,
        period_start=derived_start,
        period_end=current_ytd.period_end,
        period_type="QUARTER",
        scope=current_ytd.scope,
        unit=current_ytd.unit,
        accounting_basis=current_ytd.accounting_basis,
        formula="CURRENT_YTD - PRIOR_YTD",
        operand_record_ids=(current_ytd.record_id, prior_ytd.record_id),
        operand_document_ids=(current_ytd.document_id, prior_ytd.document_id),
        operand_pages=(current_ytd.page, prior_ytd.page),
        operand_cells=(current_ytd.cell_id, prior_ytd.cell_id),
        status=EvidenceStatus.AUTO_VERIFIED_MEDIUM,
    )
