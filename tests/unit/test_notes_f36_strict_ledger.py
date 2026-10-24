"""Pure F36 strict-ledger join (Codex 0343/0344): synthetic records in the GENUINE producer shapes, no I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from bctc_ai.notes.config_v1 import load_notes_config_v1
from bctc_ai.notes.f36_strict_ledger_v1 import (
    apply_legacy_conflicts_v1,
    classify_legacy_value_v1,
    classify_observation_v1,
    classify_rows_v1,
    classify_table_v1,
    exact_rnid_bindings_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
VID = "gfpstorev1:json:" + "9" * 64
CLOSED = {"format": "NOTES_ROOT_CLOSURE_V1", "status": "EVALUATED", "rows": [],
          "lanes": [{"lane": "c2", "status": "ROOT_CLOSED"}, {"lane": "c3", "status": "ROOT_CLOSED"}]}


@pytest.fixture(scope="module")
def config():
    return load_notes_config_v1(ROOT)


def cell(member="TAX_FEES", raw="110.573", rnid=1206, *, row=1, column="c2", ordinal=2, acceptance="ACCEPTED", **override):
    """An OPEX note cell as engine_v1 stores it (cell_json), bound to ORIGINAL (VID, s1, t1, row, column ordinal)."""

    base = {"document_ordinal": 69, "document_plan_id": "plan", "scope": "SEPARATE", "family": "OPERATING_EXPENSE",
            "concept": "OPERATING_EXPENSE_NOTE", "axis": "OPERATING_EXPENSE_LINE", "member": member,
            "classification_basis": "AS_PRESENTED", "period_key": "DURATION:YEAR:2025", "unit": "MILLION_VND",
            "observation_state": "VALUE", "value": "110573", "raw": raw, "acceptance": acceptance, "hold_reasons": [],
            "report_norm_id": rnid,
            "locator": {"page_json_version_id": VID, "section_id": "s1", "table_id": "t1", "row_id": f"r{row}", "column_id": column},
            "original_cell": {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": row,
                              "column_ordinal": ordinal, "bridge_status": "EXACT"}}
    return {**base, **override}


def inventory_row(row, values, label="Chi nộp thuế và các khoản phí, lệ phí"):
    """A neutral-inventory row record: presence/value envelopes and the value axis (types, nulls, one-LF hashes)."""

    return {"record_type": "row", "document_ordinal": 69, "page_json_version_id": VID,
            "pointer": f"/sections/0/tables/0/rows/{row - 1}", "row_ordinal": row,
            "fields": {"label_exact": {"present": True, "value": label}, "row_kind": {"present": True, "value": "ITEM"},
                       "hierarchy_path_exact": {"present": True, "value": [label]}},
            "value_axis": {"count": len(values), "item_types": [type(v).__name__ for v in values],
                           "null_column_ordinals": [c for c, v in enumerate(values, 1) if v is None],
                           "items_one_lf_sha256": [canonical_json_sha256_v1(v) for v in values]}}


COLUMNS = [{"record_type": "column", "pointer": "/sections/0/tables/0/columns/" + str(c - 1), "column_ordinal": c,
            "page_json_version_id": VID, "column_exact": {"value_kind": kind}}
           for c, kind in ((1, "TEXT"), (2, "MONEY"), (3, "MONEY"))]
ROWS = {(VID, 1, 1, 1): inventory_row(1, ["28", "110.573", "128.709"])}


def test_rnid_is_recomputed_as_the_engines_exact_binding(config):
    cells = [cell(), cell("RENT_EXPENSE", rnid=None, row=2)]
    assert exact_rnid_bindings_v1(cells, config.crosswalk) == [1206, None]
    # Several printed bases for one concept/axis: only AS_PRESENTED cells bind.
    mixed = [cell(), cell(classification_basis="BY_NATURE", row=2)]
    assert exact_rnid_bindings_v1(mixed, config.crosswalk) == [1206, None]


def test_a_preference_tuple_binds_only_the_first_member_present_in_its_own_lane():
    crosswalk = {("C", "A", ("X", "Y")): 9}
    both = [cell("X", concept="C", axis="A"), cell("Y", concept="C", axis="A", row=2)]
    assert exact_rnid_bindings_v1(both, crosswalk) == [9, None]
    alone = [cell("Y", concept="C", axis="A", row=2), cell("X", concept="C", axis="A", column="c3", ordinal=3)]
    assert exact_rnid_bindings_v1(alone, crosswalk) == [9, 9]  # each lane binds its own first present member


def test_a_closed_exactly_bound_valued_cell_is_a_core_candidate():
    record = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    assert record["class"] == "CORE_CANDIDATE" and record["lane_closure"] == "ROOT_CLOSED"


def test_a_closed_cell_without_a_template_row_is_source_only():
    rows = {(VID, 1, 1, 1): inventory_row(1, [None, "761.240", "568.282"], "Chi phí thuê tài sản")}
    assert classify_observation_v1(cell("RENT_EXPENSE", "761.240", None), None, CLOSED, rows)["class"] == "ACCEPTED_SOURCE_ONLY"


@pytest.mark.parametrize("override,binding,why", [
    ({"report_norm_id": 1207}, 1206, "RNID_IS_NOT_THE_EXACT_CROSSWALK_BINDING"),
    ({"report_norm_id": 1206}, None, "RNID_IS_NOT_THE_EXACT_CROSSWALK_BINDING"),
    ({"raw": "110,573"}, 1206, "RAW_ONE_LF_HASH_DIFFERS_FROM_ORIGINAL_ITEM"),
    ({"original_cell": None}, 1206, "ORIGINAL_COORDINATE_ABSENT"),
    ({"original_cell": {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 9,
                        "column_ordinal": 2}}, 1206, "ORIGINAL_ROW_NOT_IN_INVENTORY"),
    ({"original_cell": {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 1,
                        "column_ordinal": 4}}, 1206, "ORIGINAL_COLUMN_OUTSIDE_ROW_VALUE_AXIS"),
    ({"unit": None}, 1206, "UNIT_PERIOD_SCOPE_OR_ROLE_AXIS_MISSING"),
    ({"period_key": None}, 1206, "UNIT_PERIOD_SCOPE_OR_ROLE_AXIS_MISSING"),
    ({"scope": None}, 1206, "UNIT_PERIOD_SCOPE_OR_ROLE_AXIS_MISSING"),
])
def test_every_identity_proof_is_required_for_the_core(override, binding, why):
    assert classify_observation_v1(cell(**override), binding, CLOSED, ROWS)["class"] == f"ACCEPTED_IDENTITY_UNPROVEN:{why}"


def test_a_null_original_item_is_never_read_as_a_value():
    rows = {(VID, 1, 1, 1): inventory_row(1, ["28", None, "128.709"])}
    assert classify_observation_v1(cell(), 1206, CLOSED, rows)["class"] == \
        "ACCEPTED_IDENTITY_UNPROVEN:ORIGINAL_ITEM_NOT_A_NON_NULL_STRING"


@pytest.mark.parametrize("closure,why", [
    ({**CLOSED, "lanes": [{"lane": "c2", "status": "NOT_ROOT_CLOSED:ROOT_EQUATION_NOT_EVALUABLE"}]},
     "NOT_ROOT_CLOSED:ROOT_EQUATION_NOT_EVALUABLE"),
    ({"status": "UNRESOLVED:CONTINUATION_MERGED_TABLE_NOT_SUPPORTED_V1", "rows": [], "lanes": []},
     "UNRESOLVED:CONTINUATION_MERGED_TABLE_NOT_SUPPORTED_V1"),
    (None, "NO_CLOSURE_RESULT"),
])
def test_a_local_acceptance_without_root_closure_is_never_core(closure, why):
    assert classify_observation_v1(cell(), 1206, closure, ROWS)["class"] == f"ACCEPTED_LOCAL_NOT_ROOT_CLOSED:{why}"


@pytest.mark.parametrize("acceptance,extra,expected", [
    ("HOLD", {"hold_reasons": ["LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR", "X"]}, "HOLD:LINE_NOT_PROVEN_BY_ITS_OWN_EQUATION_OR_ANCHOR"),
    ("ACCEPTED_BLANK", {}, "ACCEPTED_PRINTED_BLANK_OR_DASH"),
    ("ACCEPTED_DASH", {}, "ACCEPTED_PRINTED_BLANK_OR_DASH"),
    ("DUPLICATE_IDENTICAL_CONTROL", {}, "DUPLICATE_IDENTICAL_CONTROL"),
    ("SOMETHING_NEW", {}, "UNKNOWN_ACCEPTANCE_STATE:SOMETHING_NEW"),
])
def test_every_acceptance_state_has_its_own_class_and_none_disappears(acceptance, extra, expected):
    assert classify_observation_v1(cell(acceptance=acceptance, **extra), 1206, CLOSED, ROWS)["class"] == expected


def test_a_read_row_keeps_every_other_valued_money_position_unread():
    rows = [inventory_row(1, ["28", "110.573", "128.709"]), inventory_row(2, [None, "5", None], "Chi khác"),
            inventory_row(3, ["x", None, None], "Ghi chú"), inventory_row(4, [None, "7", "8"], "Dòng không đọc")]
    closure = {**CLOSED, "rows": [{"row_ordinal": 2, "class": "DETAIL", "owner_row_ordinal": 1}]}
    result = {r["row_ordinal"]: r for r in classify_rows_v1(rows, COLUMNS, [cell()], closure)}
    assert result[1] == {"row_ordinal": 1, "class": "READ", "read_money_positions": [2], "unread_money_positions": [3]}
    assert result[2]["class"] == "DETAIL" and result[2]["unread_money_positions"] == [2]
    assert result[3] == {"row_ordinal": 3, "class": "BLANK_ROW", "unread_money_positions": []}  # TEXT "x" is no money
    assert result[4] == {"row_ordinal": 4, "class": "UNREAD_ORIGINAL", "unread_money_positions": [2, 3]}


def test_every_original_table_is_assessed_or_unassessed_never_absent(config):
    phrases = config.families["OPERATING_EXPENSE"].raw["subjects"]["OPERATING_EXPENSE_NOTE"]["any"]
    table = {"record_type": "table", "pointer": "/sections/0/tables/0", "page_json_version_id": VID,
             "fields": {"title_exact": {"present": True, "value": "30. Chi phí hoạt động"}}}
    target = ["OPERATING_EXPENSE", 69, VID, "s1", "t1"]
    assert classify_table_v1(table, None, {(VID, 1, 1): target}, phrases) == {
        "table": [VID, 1, 1], "class": "ASSESSED_OPEX", "target": target}
    assert classify_table_v1(table, None, {}, phrases)["tag"] == "POTENTIAL_CANDIDATE"
    other = {**table, "fields": {"title_exact": {"present": True, "value": "Tiền gửi của khách hàng"}}}
    assert classify_table_v1(other, None, {}, phrases) == {"table": [VID, 1, 1], "class": "UNASSESSED",
                                                           "tag": "NOT_SCANNED_AS_CANDIDATE"}


def _proof(status="DIRECT_LANE_COLUMN_PROVEN", rnid=1206, text="110.573", unit="MILLION_VND", row=1, column=2):
    return {"item_mapping_id": "m1", "value_index": 0, "proof_status": status, "report_norm_id": rnid, "unit": unit,
            "source_text_one_lf_sha256": canonical_json_sha256_v1(text), "coefficient": 110573,
            "original_cell": {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": row,
                              "column_ordinal": column}}


def test_legacy_values_join_only_through_a_direct_lane_column_proof():
    observation = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    by_coordinate = {(VID, 1, 1, 1, 2): observation}
    assert classify_legacy_value_v1(_proof("LEGACY_LANE_COLUMN_UNPROVEN"), by_coordinate, ROWS)["class"] == \
        "LEGACY_NOT_JOINABLE:LEGACY_LANE_COLUMN_UNPROVEN"
    assert classify_legacy_value_v1(_proof(row=7), by_coordinate, ROWS)["class"] == "LEGACY_NO_CURRENT_OBSERVATION"
    agrees = classify_legacy_value_v1(_proof(), by_coordinate, ROWS)
    assert agrees["class"] == "LEGACY_AGREES" and agrees["period"] == "LEGACY_PERIOD_UNPROVEN"
    assert classify_legacy_value_v1(_proof(rnid=1207, text="110,573"), by_coordinate, ROWS)["class"] == "LEGACY_DIFFERS:RNID,RAW"


@pytest.mark.parametrize("override,axes", [
    ({"unit": None}, "UNIT"),
    ({"unit": " "}, "UNIT"),
    ({"report_norm_id": None}, "RNID"),
    ({"report_norm_id": "1206"}, "RNID"),
    ({"report_norm_id": True}, "RNID"),
    ({"source_text_one_lf_sha256": None}, "RAW_HASH"),
    ({"source_text_one_lf_sha256": "AB" * 32}, "RAW_HASH"),
    ({"original_cell": None}, "COORDINATE"),
    ({"original_cell": {"page_json_version_id": VID, "section_ordinal": 1, "table_ordinal": 1, "row_ordinal": 1,
                        "column_ordinal": 0}}, "COORDINATE"),
    ({"item_mapping_id": None, "value_index": True}, "ITEM_MAPPING_ID,VALUE_INDEX"),
])
def test_a_missing_or_malformed_legacy_axis_never_contradicts_the_core(override, axes):
    core = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    record = classify_legacy_value_v1({**_proof(), **override}, {(VID, 1, 1, 1, 2): core}, ROWS)
    assert record["class"] == f"LEGACY_NOT_JOINABLE:AXIS_MISSING_OR_MALFORMED:{axes}"
    apply_legacy_conflicts_v1([core], [record])
    assert core["class"] == "CORE_CANDIDATE"


def test_an_unavailable_current_original_item_is_not_a_raw_difference():
    core = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    record = classify_legacy_value_v1(_proof(), {(VID, 1, 1, 1, 2): core}, {})
    assert record["class"] == "LEGACY_NOT_JOINABLE:CURRENT_ORIGINAL_ITEM_UNAVAILABLE"


def test_only_a_proven_legacy_difference_moves_a_core_candidate_to_review():
    core = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    held = classify_observation_v1(cell(acceptance="HOLD", hold_reasons=["X"], row=1), 1206, CLOSED, ROWS)
    observations = [core, held]
    by_coordinate = {(VID, 1, 1, 1, 2): core}
    legacy = [classify_legacy_value_v1(_proof(unit="VND"), by_coordinate, ROWS),
              classify_legacy_value_v1(_proof("LEGACY_PERIOD_UNPROVEN"), by_coordinate, ROWS)]
    apply_legacy_conflicts_v1(observations, legacy)
    assert core["class"] == "CONFLICT_REVIEW" and held["class"] == "HOLD:X"
    untouched = classify_observation_v1(cell(), 1206, CLOSED, ROWS)
    apply_legacy_conflicts_v1([untouched], [legacy[1]])  # an unjoinable record establishes or contradicts nothing
    assert untouched["class"] == "CORE_CANDIDATE"
