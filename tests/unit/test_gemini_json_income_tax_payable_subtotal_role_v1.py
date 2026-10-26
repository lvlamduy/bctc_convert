"""F39 weak "Thuế TNDN trong năm" payable subtotal never proves CURRENT_TAX_PARENT (Codex 0418/0421, Claude PDF review 0414).

Synthetic controls; the actual doc 225 source pilot is recorded separately.
"""
from __future__ import annotations

from copy import deepcopy

import pytest
from test_gemini_json_income_tax_family_v1 import _adapter_compiled, _page, _record, _row

from bctc_ai.evaluation import gemini_json_income_tax_family_v1 as family
from bctc_ai.evaluation.gemini_json_income_tax_family_v1 import (
    GeminiJsonIncomeTaxFamilyV1Error,
    _current_tax_payable_subtotal_conflicts_v1,
    _seal_income_tax_source_controls,
    _source_context_receipt,
    _source_money,
)
from bctc_ai.evaluation.gemini_json_multitable_hierarchical_family_v1 import READY, UNRESOLVED
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

COMPUTED = "Chi phí thuế TNDN tính trên thu nhập chịu thuế"
PRIOR = "Điều chỉnh tăng thuế TNDN phải nộp của các khoản chi phí không được khấu trừ thuế các năm trước"
WEAK = "Thuế TNDN trong năm"
STRONG = "Tổng chi phí thuế TNDN hiện hành"
REASON = "ALGORITHM_CURRENT_TAX_PARENT_PAYABLE_SUBTOTAL_ROLE_UNPROVEN"


def _seal_context(context):
    material = {key: value for key, value in context.items() if key != "receipt_id"}
    context["receipt_id"] = "gjitfav1:source-context:" + canonical_json_sha256_v1(material)


def _seal_population(population):
    material = {key: value for key, value in population.items() if key != "receipt_id"}
    population["receipt_id"] = "gjitfav1:tax-population:" + canonical_json_sha256_v1(material)


def _fixture(*, selected_label=WEAK, adjustment_label=PRIOR, adjustment_values=("-", "5"),
             include_computed=True, include_adjustment=True, with_root=False, adjustment_position="between"):
    rows = []
    adjustment = _row(adjustment_label, *adjustment_values)
    if include_adjustment and adjustment_position == "before":
        rows.append(adjustment)
    if include_computed:
        rows.append(_row(COMPUTED, "30", "20"))
    if include_adjustment and adjustment_position == "between":
        rows.append(adjustment)
    selected_ordinal = len(rows) + 1
    rows.append(_row(selected_label, "30", "25", kind="TOTAL"))
    if include_adjustment and adjustment_position == "after":
        rows.append(adjustment)
    if with_root:
        rows.append(_row("Chi phí thuế thu nhập doanh nghiệp", "30", "20", kind="TOTAL"))
    records = [_record(_page(rows))]
    compiled = _adapter_compiled()
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    population = context["tax_population_inventory"][0]

    def mapping(ordinal, role):
        source = population["source_table_row_axis"][ordinal - 1]
        return {
            "role": role, "state": "SOURCE_OBSERVED_ROLE_ROW",
            "values": [_source_money(value) for value in source["source_values_exact"]],
            "source_refs": [{"locator": deepcopy(population["locator"]), "row_ordinal": ordinal,
                             "row_id": f"r{ordinal}", "row_kind": source["row_kind"],
                             "label_exact": source["label_exact"], "hierarchy_path_exact": deepcopy(source["hierarchy_path_exact"]),
                             "money_column_ordinals": deepcopy(population["lane_axis"]["money_column_ordinals"])}],
        }
    candidate = {"status": READY, "reasons": [], "closure_receipt": {},
                 "mappings": [mapping(selected_ordinal, "CURRENT_TAX_PARENT")]}
    if with_root:
        candidate["mappings"].append(mapping(len(rows), "FAMILY_ROOT_TOTAL"))
    candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(candidate)
    return candidate, context, records, compiled


def _conflicts(fixture):
    candidate, context, records, compiled = fixture
    return _current_tax_payable_subtotal_conflicts_v1(candidate, source_context=context,
        repaired_records=records, compiled_specs=compiled)


@pytest.mark.parametrize("label", [PRIOR, PRIOR.replace("chi phí ", "chi phí\n"),
                                  "Điều chỉnh giảm thuế thu nhập doanh nghiệp phải nộp các năm trước"])
def test_exact_printed_prior_payable_tokens_withhold_weak_subtotal(label):
    fixture = _fixture(adjustment_label=label)
    before = deepcopy(fixture[:3])
    conflicts = _conflicts(fixture)
    assert len(conflicts) == 1
    proof = conflicts[0]
    assert proof["status"] == "ALGORITHM_HOLD"
    assert proof["classification"] == "ALGORITHM_ROLE_UNPROVEN"
    assert proof["source_values_changed"] is False
    assert proof["computed_tax_source_row"]["row_ordinal"] == 1
    assert proof["intervening_prior_year_adjustment_rows"][0]["row_ordinal"] == 2
    assert proof["weak_subtotal_source_row"]["row_ordinal"] == 3
    assert proof["source_population_sha256"] == canonical_json_sha256_v1(fixture[1]["tax_population_inventory"][0])
    assert fixture[:3] == before


@pytest.mark.parametrize("values", [("0", "0"), ("-", "-"), (None, None), ("-", "5")])
def test_prior_values_do_not_supply_the_role_or_disable_the_hold(values):
    fixture = _fixture(adjustment_values=values)
    proof = _conflicts(fixture)[0]
    assert proof["intervening_prior_year_adjustment_rows"][0]["source_values_exact"] == list(values)


@pytest.mark.parametrize("with_root", [False, True])
def test_ready_seal_withholds_all_mappings_before_other_controls_with_or_without_root(with_root):
    candidate, context, records, compiled = _fixture(with_root=with_root)
    before = deepcopy(candidate)
    result = _seal_income_tax_source_controls(candidate, source_context=context, repaired_records=records, compiled_specs=compiled)
    assert result["status"] == UNRESOLVED
    assert result["mappings"] == []
    assert result["reasons"] == [REASON]
    evidence = result["closure_receipt"]["income_tax_unresolved_evidence_receipt"]
    assert evidence["evidence"]["classification"] == "ALGORITHM_ROLE_UNPROVEN"
    material = {key: value for key, value in evidence.items() if key != "receipt_id"}
    assert evidence["receipt_id"] == "gjitfav1:unresolved:" + canonical_json_sha256_v1(material)
    assert candidate == before


@pytest.mark.parametrize("label", [STRONG, "Chi phí thuế TNDN hiện hành", COMPUTED])
def test_strong_current_expense_or_computed_source_label_is_unchanged(label):
    assert _conflicts(_fixture(selected_label=label)) == []


@pytest.mark.parametrize("include_computed,include_adjustment", [(False, True), (True, False), (False, False)])
def test_missing_sequence_member_does_not_invent_a_payable_subtotal_conflict(include_computed, include_adjustment):
    assert _conflicts(_fixture(include_computed=include_computed, include_adjustment=include_adjustment)) == []


@pytest.mark.parametrize("position", ["before", "after"])
def test_prior_adjustment_outside_computed_to_selected_interval_does_not_borrow_ownership(position):
    assert _conflicts(_fixture(adjustment_position=position)) == []


@pytest.mark.parametrize("label", ["Điều chỉnh thuế TNDN phải nộp trong năm", "Thuế TNDN phải nộp các năm trước",
                                  "Điều chỉnh chi phí các năm trước", "Phải nộp thuế TNDN các năm trước"])
def test_untyped_partial_marker_set_does_not_match_payable_prior_year_adjustment(label):
    fixture = _fixture(adjustment_label=label)
    # These synthetic labels are deliberately outside the production role aliases.
    assert fixture[1]["tax_population_inventory"][0]["source_table_row_axis"][1]["matched_role"] is None
    assert _conflicts(fixture) == []


def test_different_table_adverse_sequence_cannot_supply_selected_table_interval():
    candidate, _context, records, compiled = _fixture(include_adjustment=False)
    adverse = _fixture()[2][0]["page_json"]["sections"][0]["tables"][0]
    records[0]["page_json"]["sections"][0]["tables"].append(deepcopy(adverse))
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    assert _conflicts((candidate, context, records, compiled)) == []


def test_other_document_adverse_sequence_cannot_supply_selected_document_interval():
    own = _fixture(include_adjustment=False)
    assert _conflicts(own) == []
    foreign_candidate, _old_context, foreign_records, compiled = _fixture()
    foreign_records[0].update(document_id="gfpstorev1:document:" + "d" * 64, document_ordinal=2,
                              page_json_version_id="gfpstorev1:json:" + "e" * 64, selected_page_ordinal=2,
                              source_logical_name="other-fixture.pdf", source_sha256="f" * 64)
    # Each context is rebuilt from ONE independent source identity. Never reseal
    # a mixed-document context and present that envelope as production-valid.
    foreign_context = _source_context_receipt(
        compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=foreign_records,
    )
    foreign_candidate["mappings"][0]["source_refs"][0]["locator"] = deepcopy(
        foreign_context["tax_population_inventory"][0]["locator"],
    )
    foreign_candidate["candidate_id"] = "gjmthfcv1:candidate:" + canonical_json_sha256_v1(
        {key: value for key, value in foreign_candidate.items() if key != "candidate_id"},
    )
    assert len(_conflicts((foreign_candidate, foreign_context, foreign_records, compiled))) == 1
    candidate, _context, records, compiled = own
    # Supplying the independently valid foreign population for our selected
    # source cannot borrow its adverse interval: the exact nine-key join fails.
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="population join is not unique"):
        _conflicts((candidate, foreign_context, records, compiled))


@pytest.mark.parametrize("drift", ["context", "population", "source_page", "source_row_axis", "row_ordinal", "row_fields", "money_axis"])
def test_receipt_or_selected_source_drift_raises_instead_of_receiving_a_financial_disposition(drift):
    fixture = _fixture()
    candidate, context, records, _compiled = fixture
    population = context["tax_population_inventory"][0]
    ref = candidate["mappings"][0]["source_refs"][0]
    if drift == "context":
        context["rule"] = "changed"
    elif drift == "population":
        population["rule"] = "changed"
        _seal_context(context)
    elif drift == "source_page":
        records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["values_exact"][0] = "31"
    elif drift == "source_row_axis":
        population["source_table_row_axis"][0]["matched_role"] = None
        _seal_population(population)
        _seal_context(context)
    elif drift == "row_ordinal":
        ref["row_ordinal"] = 99
    elif drift == "row_fields":
        ref["hierarchy_path_exact"] = ["Different owner", WEAK]
    else:
        ref["money_column_ordinals"] = [2, 1]
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="payable-subtotal"):
        _conflicts(fixture)


def test_duplicate_exact_population_join_raises():
    fixture = _fixture()
    fixture[1]["tax_population_inventory"].append(deepcopy(fixture[1]["tax_population_inventory"][0]))
    _seal_context(fixture[1])
    with pytest.raises(GeminiJsonIncomeTaxFamilyV1Error, match="population join is not unique"):
        _conflicts(fixture)


def test_nonready_candidate_is_retained_before_the_new_guard():
    candidate, _context, _records, compiled = _fixture()
    candidate.update(status=UNRESOLVED, mappings=[], reasons=["EXISTING_HOLD"])
    result = _seal_income_tax_source_controls(candidate, source_context={}, repaired_records=[], compiled_specs=compiled)
    assert result == candidate
    assert result is not candidate


def test_absent_selected_current_role_does_not_scan_unrelated_payable_rows():
    fixture = _fixture()
    fixture[0]["mappings"] = []
    assert _conflicts(fixture) == []


def test_existing_typed_prior_period_tax_adjustment_role_also_withholds_weak_subtotal():
    fixture = _fixture(adjustment_label="Điều chỉnh thuế TNDN các năm trước")
    assert fixture[1]["tax_population_inventory"][0]["source_table_row_axis"][1]["matched_role"] == "PRIOR_PERIOD_TAX_ADJUSTMENT"
    assert len(_conflicts(fixture)) == 1


def test_primary_statement_weak_label_is_outside_this_note_sequence_guard():
    candidate, _context, records, compiled = _fixture()
    records[0]["page_json"]["sections"][0]["content_kind"] = "PRIMARY_STATEMENT"
    assert _conflicts((candidate, {}, records, compiled)) == []


def test_intervening_group_reset_does_not_borrow_a_different_printed_population():
    candidate, _context, records, compiled = _fixture()
    records[0]["page_json"]["sections"][0]["tables"][0]["rows"].insert(1, _row("Nhóm khác", None, None, kind="GROUP"))
    ref = candidate["mappings"][0]["source_refs"][0]
    ref.update(row_ordinal=4, row_id="r4")
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    assert _conflicts((candidate, context, records, compiled)) == []


def test_different_printed_computed_row_ancestry_does_not_supply_selected_population():
    candidate, _context, records, compiled = _fixture()
    records[0]["page_json"]["sections"][0]["tables"][0]["rows"][0]["hierarchy_path_exact"] = ["Nhóm khác", COMPUTED]
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    assert _conflicts((candidate, context, records, compiled)) == []


def test_same_explicit_printed_ancestry_retains_the_owned_sequence_hold():
    candidate, _context, records, compiled = _fixture()
    for row in records[0]["page_json"]["sections"][0]["tables"][0]["rows"]:
        row["hierarchy_path_exact"] = ["Đối chiếu thuế", row["label_exact"]]
    candidate["mappings"][0]["source_refs"][0]["hierarchy_path_exact"] = ["Đối chiếu thuế", WEAK]
    context = _source_context_receipt(compiled_specs=compiled, repair_receipts=[], root_controls=[], page_records=records)
    assert len(_conflicts((candidate, context, records, compiled))) == 1


def test_production_status_constants_reach_guard_and_preserve_nonready_short_circuit(monkeypatch):
    candidate, context, records, compiled = _fixture()
    assert candidate["status"] == READY
    original = family._current_tax_payable_subtotal_conflicts_v1
    entered = []

    def observed(*args, **kwargs):
        entered.append(args[0]["status"])
        return original(*args, **kwargs)

    monkeypatch.setattr(family, "_current_tax_payable_subtotal_conflicts_v1", observed)
    result = family._seal_income_tax_source_controls(
        candidate, source_context=context, repaired_records=records, compiled_specs=compiled,
    )
    assert entered == [READY]
    assert result["status"] == UNRESOLVED and result["reasons"] == [REASON]
    held = deepcopy(candidate)
    held.update(status=UNRESOLVED, mappings=[], reasons=["EXISTING_HOLD"])
    assert family._seal_income_tax_source_controls(
        held, source_context={}, repaired_records=[], compiled_specs=compiled,
    ) == held
    assert entered == [READY]
