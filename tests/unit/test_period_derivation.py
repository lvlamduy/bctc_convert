from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from bctc_ai.axes.derivation import PeriodDerivationError, PeriodValue, derive_quarter_from_ytd
from bctc_ai.core.contracts import EvidenceStatus


def _value(identifier: str, end: date, value: str, **overrides) -> PeriodValue:
    fields = {
        "record_id": identifier,
        "document_id": f"doc-{identifier}",
        "schema_id": 4399,
        "statement_type": "KQKD",
        "value": Decimal(value),
        "period_start": date(2026, 1, 1),
        "period_end": end,
        "period_type": "YTD",
        "scope": "CONSOLIDATED",
        "unit": "VND_MILLION",
        "accounting_basis": "VAS",
        "status": EvidenceStatus.AUTO_VERIFIED_HIGH,
        "page": 8,
        "cell_id": f"cell-{identifier}",
        "source_visible": True,
    }
    fields.update(overrides)
    return PeriodValue(**fields)


def test_ytd_difference_has_two_cell_provenances_and_cannot_be_high():
    q1 = _value("q1", date(2026, 3, 31), "100")
    q2_ytd = _value("q2-ytd", date(2026, 6, 30), "260")
    derived = derive_quarter_from_ytd(q2_ytd, q1)
    assert derived.value == Decimal("160")
    assert derived.period_start == date(2026, 4, 1)
    assert derived.period_end == date(2026, 6, 30)
    assert derived.formula == "CURRENT_YTD - PRIOR_YTD"
    assert derived.operand_record_ids == ("q2-ytd", "q1")
    assert derived.status is EvidenceStatus.AUTO_VERIFIED_MEDIUM
    assert not derived.directly_observed


def test_derivation_rejects_scope_or_unit_mismatch():
    q1 = _value("q1", date(2026, 3, 31), "100")
    q2 = _value("q2", date(2026, 6, 30), "260", scope="SEPARATE")
    with pytest.raises(PeriodDerivationError, match="scope"):
        derive_quarter_from_ytd(q2, q1)


def test_derivation_rejects_nonadjacent_or_unseen_operands():
    q1 = _value("q1", date(2026, 3, 31), "100", source_visible=False)
    q3 = _value("q3", date(2026, 9, 30), "300")
    with pytest.raises(PeriodDerivationError):
        derive_quarter_from_ytd(q3, q1)
