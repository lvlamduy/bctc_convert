from __future__ import annotations

from decimal import Decimal

from bctc_ai.validation.arithmetic import (
    NumericOperand,
    ValidationResult,
    check_horizontal_total,
    check_parent_children,
    check_vertical_total,
)


def test_parent_child_and_axis_sums_are_validation_only():
    total = NumericOperand("parent", Decimal("100"))
    children = [NumericOperand("c1", Decimal("40")), NumericOperand("c2", Decimal("60"))]
    for finding in (
        check_parent_children(total, children),
        check_horizontal_total(total, children),
        check_vertical_total(total, children),
    ):
        assert finding.result is ValidationResult.PASS
        assert not finding.may_generate_value


def test_failed_sum_requests_reread_without_repairing_value():
    finding = check_parent_children(
        NumericOperand("parent", Decimal("101")),
        [NumericOperand("c1", Decimal("40")), NumericOperand("c2", Decimal("60"))],
    )
    assert finding.result is ValidationResult.FAIL
    assert finding.residual == Decimal("1")
    assert "reread source cells" in finding.remediation
    assert not finding.may_generate_value


def test_missing_operand_is_not_treated_as_zero():
    finding = check_vertical_total(
        NumericOperand("total", Decimal("10")),
        [NumericOperand("visible", Decimal("10")), NumericOperand("blank", None)],
    )
    assert finding.result is ValidationResult.NOT_TESTABLE
    assert finding.expected is None
