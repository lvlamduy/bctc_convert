"""Synthetic pure projection boundaries, not source authentication or admission."""

from __future__ import annotations

from copy import deepcopy

import pytest
from test_notes_f36_strict_ledger import CLOSED, ROWS, _proof, cell, inventory_row

from bctc_ai.notes.f36_ledger_projection_v1 import (
    LedgerProjectionError,
    attach_f36_ledger_v1,
    strict_f36_core_eligibility_v1,
)
from bctc_ai.notes.f36_strict_ledger_v1 import (
    apply_legacy_conflicts_v1,
    classify_legacy_value_v1,
    classify_observation_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_bytes_v1

REFS = {name: {"path": f"/synthetic/{name}.json", "sha256": digit * 64, "size_bytes": 9}
        for name, digit in (("summary", "a"), ("observations", "b"))}


def _core():
    original = cell()
    return original, classify_observation_v1(original, 1206, CLOSED, ROWS)


def test_full_store_order_and_every_original_field_survive_with_real_classifier_records():
    original, core = _core()
    source = cell("RENT_EXPENSE", "761.240", None, row=2, value="761240")
    source_rows = {(source["original_cell"]["page_json_version_id"], 1, 1, 2):
                   inventory_row(2, [None, "761.240", "568.282"], "Chi phí thuê tài sản")}
    source_record = classify_observation_v1(source, None, CLOSED, source_rows)
    foreign = {"family": "INCOME_TAX", "raw": None, "nested": [{"unresolved": True}]}
    cells = [foreign, source, original]
    before = canonical_json_bytes_v1(cells)
    joined = attach_f36_ledger_v1(cells, [core, source_record], ledger_input_refs=REFS)
    restored = [{k: v for k, v in c.items() if k not in {"ledger_class", "ledger_evidence"}} for c in joined]
    assert canonical_json_bytes_v1(restored) == before == canonical_json_bytes_v1(cells)
    assert joined[0] == foreign and "ledger_class" not in joined[0]
    assert [c.get("ledger_class") for c in joined] == [None, "ACCEPTED_SOURCE_ONLY", "CORE_CANDIDATE"]
    assert strict_f36_core_eligibility_v1(joined) == [False, False, True]
    assert joined[2]["ledger_evidence"]["input_refs"] == REFS
    assert joined[2]["ledger_evidence"]["authentication_performed"] is False


def test_results_and_inputs_have_no_mutable_container_aliases_in_either_direction():
    original, record = _core()
    cells, records, refs = [original], [record], deepcopy(REFS)
    baseline = canonical_json_bytes_v1([cells, records, refs])
    joined = attach_f36_ledger_v1(cells, records, ledger_input_refs=refs)
    joined[0]["locator"]["row_id"] = "changed"
    joined[0]["ledger_evidence"]["classification"]["cell"]["hold_reasons"].append("changed")
    joined[0]["ledger_evidence"]["input_refs"]["summary"]["path"] = "changed"
    assert canonical_json_bytes_v1([cells, records, refs]) == baseline
    fresh = attach_f36_ledger_v1(cells, records, ledger_input_refs=refs)
    cells[0]["locator"]["row_id"] = "changed"
    records[0]["lane_closure"] = "changed"
    refs["summary"]["path"] = "changed"
    assert fresh[0]["locator"]["row_id"] == "r1"
    assert strict_f36_core_eligibility_v1(fresh) == [True]


@pytest.mark.parametrize("attack", ["missing", "extra", "duplicate_record", "duplicate_cell"])
def test_join_refuses_any_ledger_or_store_cardinality_gap_without_mutation(attack):
    original, core = _core()
    cells, records = [original], [core]
    if attack == "missing":
        records = []
    elif attack == "extra":
        extra = cell(row=2)
        records.append(classify_observation_v1(extra, 1206, CLOSED, ROWS))
    elif attack == "duplicate_record":
        records.append(deepcopy(core))
    else:
        cells.append(deepcopy(original))
    before = canonical_json_bytes_v1([cells, records])
    with pytest.raises(LedgerProjectionError):
        attach_f36_ledger_v1(cells, records, ledger_input_refs=REFS)
    assert canonical_json_bytes_v1([cells, records]) == before


@pytest.mark.parametrize("field,value", [
    ("value", "110574"), ("raw", "110,573"), ("unit", "THOUSAND_VND"),
    ("period_key", "DURATION:YEAR:2024"), ("scope", "CONSOLIDATED"),
    ("acceptance", "HOLD"), ("document_ordinal", 70), ("document_plan_id", "other"),
    ("locator", {"column_id": "c3"}), ("original_cell", None),
])
def test_full_identity_join_does_not_fall_back_to_amount_or_partial_write_key(field, value):
    original, core = _core()
    changed = {**original, field: value}
    with pytest.raises(LedgerProjectionError):
        attach_f36_ledger_v1([changed], [core], ledger_input_refs=REFS)


@pytest.mark.parametrize("attack", ["unknown", "empty_reason", "unknown_acceptance", "missing_field", "extra_field",
                                  "binding", "bool_binding", "wrong_acceptance", "fake_conflict"])
def test_malformed_or_unknown_classifications_never_return_a_projection(attack):
    original, record = _core()
    if attack == "unknown":
        record["class"] = "ACCEPTED_CORE"
    elif attack == "empty_reason":
        record["class"] = "ACCEPTED_IDENTITY_UNPROVEN:"
    elif attack == "unknown_acceptance":
        record["class"] = "UNKNOWN_ACCEPTANCE_STATE:FUTURE"
    elif attack == "missing_field":
        del record["exact_rnid_binding"]
    elif attack == "extra_field":
        record["authority_granted"] = True
    elif attack == "binding":
        record["exact_rnid_binding"] = 1207
    elif attack == "bool_binding":
        record["exact_rnid_binding"] = True
    elif attack == "wrong_acceptance":
        record["cell"] = {**original, "acceptance": "HOLD"}
    else:
        record["class"] = "CONFLICT_REVIEW"
    with pytest.raises(LedgerProjectionError):
        attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)


@pytest.mark.parametrize("acceptance,extra,expected", [
    ("HOLD", {"hold_reasons": ["INCOMPLETE_PRINTED_FRONTIER:X"]}, "HOLD:INCOMPLETE_PRINTED_FRONTIER"),
    ("ACCEPTED_BLANK", {"observation_state": "BLANK", "value": None, "raw": None}, "ACCEPTED_PRINTED_BLANK_OR_DASH"),
    ("ACCEPTED_DASH", {"observation_state": "DASH", "value": None, "raw": "-"}, "ACCEPTED_PRINTED_BLANK_OR_DASH"),
    ("DUPLICATE_IDENTICAL_CONTROL", {}, "DUPLICATE_IDENTICAL_CONTROL"),
])
def test_unresolved_blank_dash_and_control_stay_distinct_and_never_numeric_core(acceptance, extra, expected):
    original = cell(acceptance=acceptance, **extra)
    record = classify_observation_v1(original, 1206, CLOSED, ROWS)
    joined = attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)
    assert joined[0]["ledger_class"] == expected
    assert joined[0]["acceptance"] == acceptance
    assert joined[0]["value"] == original["value"]
    assert strict_f36_core_eligibility_v1(joined) == [False]


@pytest.mark.parametrize("closure", [None, {**CLOSED, "lanes": []}])
def test_locally_accepted_cells_remain_visible_but_not_core(closure):
    original = cell()
    record = classify_observation_v1(original, 1206, closure, ROWS)
    joined = attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)
    assert joined[0]["ledger_class"].startswith("ACCEPTED_LOCAL_NOT_ROOT_CLOSED:")
    assert strict_f36_core_eligibility_v1(joined) == [False]


@pytest.mark.parametrize("kind", ["identity", "conflict"])
def test_identity_backlog_and_real_classifier_legacy_conflict_remain_non_core(kind):
    original, record = _core()
    if kind == "identity":
        original = cell(raw="110,573")
        record = classify_observation_v1(original, 1206, CLOSED, ROWS)
        expected = "ACCEPTED_IDENTITY_UNPROVEN:RAW_ONE_LF_HASH_DIFFERS_FROM_ORIGINAL_ITEM"
    else:
        key = (original["original_cell"]["page_json_version_id"], 1, 1, 1, 2)
        legacy = classify_legacy_value_v1(_proof(unit="VND"), {key: record}, ROWS)
        apply_legacy_conflicts_v1([record], [legacy])
        expected = "CONFLICT_REVIEW"
    joined = attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)
    assert joined[0]["ledger_class"] == expected
    assert joined[0]["acceptance"] == "ACCEPTED"
    assert strict_f36_core_eligibility_v1(joined) == [False]


@pytest.mark.parametrize("state,value,eligible", [("VALUE", "-110573", True), ("PRINTED_ZERO", "0", True),
                                                 ("BLANK", None, False), ("DASH", None, False),
                                                 ("VALUE", "NaN", False), ("VALUE", "Infinity", False),
                                                 ("VALUE", True, False), ("VALUE", "unparsed", False),
                                                 ("PRINTED_ZERO", "7", False)])
def test_numeric_eligibility_uses_existing_state_and_finite_stored_value_without_zero_inference(state, value, eligible):
    raw = value if eligible else "110.573"
    original = cell(observation_state=state, value=value, raw=raw)
    inventory = {(original["original_cell"]["page_json_version_id"], 1, 1, 1):
                 inventory_row(1, [None, raw, "128.709"])}
    record = classify_observation_v1(original, 1206, CLOSED, inventory)
    if eligible:
        joined = attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)
        assert strict_f36_core_eligibility_v1(joined) == [True]
        assert joined[0]["value"] == value
    else:
        with pytest.raises(LedgerProjectionError):
            attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)


@pytest.mark.parametrize("attack", ["missing_ref", "bad_hash", "bool_size", "blank_path", "ref_extra", "reserved"])
def test_pinned_ref_structure_and_reserved_field_collisions_fail_closed(attack):
    original, record = _core()
    refs = deepcopy(REFS)
    if attack == "missing_ref":
        del refs["summary"]
    elif attack == "bad_hash":
        refs["summary"]["sha256"] = "not-a-hash"
    elif attack == "bool_size":
        refs["summary"]["size_bytes"] = True
    elif attack == "blank_path":
        refs["summary"]["path"] = " "
    elif attack == "ref_extra":
        refs["summary"]["authenticated"] = True
    else:
        original["ledger_class"] = "CORE_CANDIDATE"
    with pytest.raises(LedgerProjectionError):
        attach_f36_ledger_v1([original], [record], ledger_input_refs=refs)


@pytest.mark.parametrize("attack", ["value", "class", "evidence", "claim", "record"])
def test_eligibility_refuses_mutated_attachment_instead_of_trusting_a_json_class_flag(attack):
    original, record = _core()
    joined = attach_f36_ledger_v1([original], [record], ledger_input_refs=REFS)
    if attack == "value":
        joined[0]["value"] = "999999"
    elif attack == "class":
        joined[0]["ledger_class"] = "ACCEPTED_SOURCE_ONLY"
    elif attack == "evidence":
        del joined[0]["ledger_evidence"]
    elif attack == "claim":
        joined[0]["ledger_evidence"]["authentication_performed"] = True
    else:
        joined[0]["ledger_evidence"]["classification"]["cell"]["locator"]["row_id"] = "r2"
    with pytest.raises(LedgerProjectionError):
        strict_f36_core_eligibility_v1(joined)
