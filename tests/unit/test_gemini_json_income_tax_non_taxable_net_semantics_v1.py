"""F39 NON_TAXABLE_AGGREGATE net-positive / mixed "tăng/(giảm)" semantic hold (Claude PDF review 0414, owner decision 0457).

Synthetic controls; the actual 045/221/223 source pilot is recorded separately.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_payable_subtotal_role_v1 import STRONG, _fixture

from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    READY,
    UNRESOLVED,
    _non_taxable_net_semantic_conflicts_v1,
    _seal_income_tax_source_controls,
)

REASON = "ALGORITHM_NON_TAXABLE_AGGREGATE_NET_SEMANTICS_UNPROVEN"


def _mapping(label, coefficients, state="SOURCE_OBSERVED_ROLE_ROW"):
    return {"role": "NON_TAXABLE_AGGREGATE", "state": state,
            "values": [{"coefficient": c, "source_text": None if c is None else str(c), "state": "RAW_SIGNED_INTEGER"}
                       for c in coefficients],
            "source_refs": [{"label_exact": label, "row_ordinal": 2}]}


@pytest.mark.parametrize("coefficients", [(1421, -2987), (-60, 0), (864460, -1325256), (5, 7)])
def test_any_positive_lane_is_held(coefficients):
    conflicts = _non_taxable_net_semantic_conflicts_v1({"mappings": [_mapping("Thu nhập không chịu thuế", coefficients)]})
    positive = [i for i, c in enumerate(coefficients) if c > 0]
    assert bool(conflicts) == bool(positive)
    if conflicts:
        assert conflicts[0]["positive_lane_indexes"] == positive


@pytest.mark.parametrize("label", ["- Điều chỉnh tăng/ (giảm) thu nhập chịu thuế", "Điều chỉnh tăng/(giảm) thu nhập chịu thuế"])
def test_mixed_increase_decrease_label_is_held_even_when_negative(label):
    conflicts = _non_taxable_net_semantic_conflicts_v1({"mappings": [_mapping(label, (-1, -2))]})
    assert len(conflicts) == 1 and conflicts[0]["mixed_increase_decrease_labels"] == [label]


@pytest.mark.parametrize("label", ["Thu nhập không chịu thuế", "- Điều chỉnh giảm thu nhập chịu thuế",
                                   "- Lợi nhuận của công ty con", "- Thu nhập từ góp vốn, mua cổ phần"])
def test_negative_or_dash_non_taxable_rows_are_unchanged(label):
    assert _non_taxable_net_semantic_conflicts_v1({"mappings": [_mapping(label, (-14490, None))]}) == []


def test_other_roles_are_never_inspected():
    mapping = dict(_mapping("Chi phí không được khấu trừ thuế", (42687, 43356)), role="NON_DEDUCTIBLE_EXPENSE")
    assert _non_taxable_net_semantic_conflicts_v1({"mappings": [mapping]}) == []


def test_ready_seal_withholds_the_whole_candidate_without_rewriting_values():
    candidate, context, records, compiled = _fixture(selected_label=STRONG)
    candidate = deepcopy(candidate)
    candidate["mappings"].append(_mapping("- Lợi nhuận của công ty con", (1421, -2987)))
    assert candidate["status"] == READY
    before = deepcopy(candidate)
    result = _seal_income_tax_source_controls(candidate, source_context=context, repaired_records=records,
                                              compiled_specs=compiled)
    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == [REASON]
    evidence = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]["evidence"]
    assert evidence["non_taxable_net_semantic_conflicts"][0]["mapping"]["values"][0]["coefficient"] == 1421
    assert candidate == before


def test_ready_seal_is_unchanged_without_a_non_taxable_conflict():
    candidate, context, records, compiled = _fixture(selected_label=STRONG)
    result = _seal_income_tax_source_controls(candidate, source_context=context, repaired_records=records,
                                              compiled_specs=compiled)
    assert result["status"] != UNRESOLVED or REASON not in result["reasons"]
