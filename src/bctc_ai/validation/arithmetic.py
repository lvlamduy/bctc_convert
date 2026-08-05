from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class ValidationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_TESTABLE = "NOT_TESTABLE"


@dataclass(frozen=True)
class NumericOperand:
    operand_id: str
    value: Decimal | None
    page: int | None = None
    cell_id: str | None = None


@dataclass(frozen=True)
class ValidationFinding:
    check_type: str
    result: ValidationResult
    expected: Decimal | None
    observed: Decimal | None
    residual: Decimal | None
    tolerance: Decimal
    operand_ids: tuple[str, ...]
    remediation: tuple[str, ...]
    may_generate_value: bool = False


def check_sum(
    total: NumericOperand,
    components: list[NumericOperand],
    *,
    check_type: str,
    tolerance: Decimal = Decimal("0"),
) -> ValidationFinding:
    operands = [total, *components]
    if total.value is None or not components or any(item.value is None for item in components):
        return ValidationFinding(
            check_type=check_type,
            result=ValidationResult.NOT_TESTABLE,
            expected=None,
            observed=total.value,
            residual=None,
            tolerance=tolerance,
            operand_ids=tuple(item.operand_id for item in operands),
            remediation=("collect missing visible operands",),
        )
    expected = sum((item.value for item in components if item.value is not None), Decimal("0"))
    residual = total.value - expected
    result = ValidationResult.PASS if abs(residual) <= tolerance else ValidationResult.FAIL
    remediation = (
        ()
        if result is ValidationResult.PASS
        else (
            "reread source cells",
            "check sign",
            "check period and unit",
            "check row/column binding",
            "check statement branch",
        )
    )
    return ValidationFinding(
        check_type=check_type,
        result=result,
        expected=expected,
        observed=total.value,
        residual=residual,
        tolerance=tolerance,
        operand_ids=tuple(item.operand_id for item in operands),
        remediation=remediation,
    )


def check_parent_children(
    parent: NumericOperand,
    children: list[NumericOperand],
    *,
    tolerance: Decimal = Decimal("0"),
) -> ValidationFinding:
    return check_sum(parent, children, check_type="PARENT_EQUALS_CHILDREN", tolerance=tolerance)


def check_horizontal_total(
    total: NumericOperand,
    cells: list[NumericOperand],
    *,
    tolerance: Decimal = Decimal("0"),
) -> ValidationFinding:
    return check_sum(total, cells, check_type="HORIZONTAL_TOTAL", tolerance=tolerance)


def check_vertical_total(
    total: NumericOperand,
    rows: list[NumericOperand],
    *,
    tolerance: Decimal = Decimal("0"),
) -> ValidationFinding:
    return check_sum(total, rows, check_type="VERTICAL_TOTAL", tolerance=tolerance)
